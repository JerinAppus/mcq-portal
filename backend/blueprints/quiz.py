import random
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.models import db, User, MCQ, Attempt, Stats
from backend.utils.helpers import calculate_streak_and_xp

quiz_bp = Blueprint('quiz', __name__)

@quiz_bp.route('/questions', methods=['GET'])
def get_questions():
    """Fetches a set of randomized MCQ questions. Excludes correct answers for security."""
    category = request.args.get('category')
    difficulty = request.args.get('difficulty')
    limit = request.args.get('limit', 10, type=int)

    query = MCQ.query

    if category and category != 'All':
        query = query.filter_by(category=category)
    if difficulty and difficulty != 'All':
        query = query.filter_by(difficulty=difficulty)

    all_questions = query.all()
    
    # Randomize
    selected = random.sample(all_questions, min(len(all_questions), limit))

    # Serialize without correct_answer to prevent inspect-element cheating
    return jsonify([q.to_dict(include_correct=False) for q in selected]), 200


@quiz_bp.route('/submit', methods=['POST'])
@jwt_required()
def submit_quiz():
    """
    Submits student answers, grades the quiz server-side,
    awards XP, increments streaks, and updates student statistics.
    """
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    if not user:
        return jsonify({"msg": "User not found"}), 404

    data = request.get_json() or {}
    user_answers = data.get('answers', {}) # e.g. {"4": "B", "9": "A"}

    if not user_answers:
        return jsonify({"msg": "No answers provided"}), 400

    # Fetch corresponding MCQs from DB to calculate score securely
    mcq_ids = [int(qid) for qid in user_answers.keys()]
    mcqs = MCQ.query.filter(MCQ.id.in_(mcq_ids)).all()
    mcq_map = {m.id: m for m in mcqs}

    correct_count = 0
    total_questions = len(mcq_ids)
    breakdown = []

    for qid in mcq_ids:
        mcq = mcq_map.get(qid)
        if not mcq:
            continue
        
        user_ans = user_answers.get(str(qid))
        is_correct = (user_ans == mcq.correct_answer)
        
        if is_correct:
            correct_count += 1

        breakdown.append({
            "id": mcq.id,
            "question": mcq.question,
            "option_a": mcq.option_a,
            "option_b": mcq.option_b,
            "option_c": mcq.option_c,
            "option_d": mcq.option_d,
            "user_answer": user_ans,
            "correct_answer": mcq.correct_answer,
            "is_correct": is_correct
        })

    accuracy = (correct_count / total_questions) * 100 if total_questions > 0 else 0

    try:
        # Get user's last attempt to compute streaks
        last_attempt = Attempt.query.filter_by(user_id=user.id).order_by(Attempt.submitted_at.desc()).first()

        # Update streak, XP, badge
        new_streak, xp_earned, new_badge = calculate_streak_and_xp(user, correct_count, total_questions, last_attempt)

        # Apply user rewards
        user.streak = new_streak
        user.xp_points += xp_earned
        user.badge = new_badge

        # Save Attempt
        new_attempt = Attempt(
            user_id=user.id,
            score=correct_count,
            total_questions=total_questions,
            accuracy=accuracy
        )
        db.session.add(new_attempt)

        # Update Stats
        stats = user.stats
        if not stats:
            stats = Stats(user_id=user.id)
            db.session.add(stats)

        # Recalculate aggregates
        if correct_count > stats.highest_score:
            stats.highest_score = correct_count

        old_attempts = stats.total_attempts
        new_attempts = old_attempts + 1
        stats.total_attempts = new_attempts

        # Average Score recalculation
        stats.average_score = ((stats.average_score * old_attempts) + correct_count) / new_attempts

        # Win Ratio (Total correct / Total attempted questions across all time)
        # We can calculate this by taking the sum of scores / sum of questions.
        # But we can approximate it or keep accurate count. Let's do it by loading all attempts.
        all_attempts = Attempt.query.filter_by(user_id=user.id).all()
        total_correct_all_time = sum(a.score for a in all_attempts) + correct_count
        total_questions_all_time = sum(a.total_questions for a in all_attempts) + total_questions
        
        stats.win_ratio = (total_correct_all_time / total_questions_all_time) * 100 if total_questions_all_time > 0 else 0.0
        stats.current_streak = new_streak

        db.session.commit()

        return jsonify({
            "msg": "Quiz submitted successfully",
            "score": correct_count,
            "total_questions": total_questions,
            "accuracy": round(accuracy, 2),
            "xp_earned": xp_earned,
            "new_streak": new_streak,
            "badge": new_badge,
            "breakdown": breakdown
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Submission failed: {str(e)}"}), 500
