from flask import Blueprint, request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from backend.models import db, MCQ, User, Attempt, Stats

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
def check_admin_privileges():
    """Enforces JWT authentication and restricts access exclusively to the 'admin' account."""
    # Skip CORS preflight OPTIONS requests automatically
    if request.method == "OPTIONS":
        return
        
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        import os
        admin_user = os.environ.get('ADMIN_USERNAME', 'jerin_admin')
        if not user or user.username != admin_user:
            return jsonify({"msg": "Admin access required. Unauthorized."}), 403
    except Exception as e:
        return jsonify({"msg": "Authentication required. Admin token missing or invalid."}), 401

@admin_bp.route('/mcqs', methods=['GET'])
def get_all_questions():
    """Lists all questions in the bank, including the correct answers."""
    questions = MCQ.query.order_by(MCQ.id.desc()).all()
    return jsonify([q.to_dict(include_correct=True) for q in questions]), 200


@admin_bp.route('/mcqs', methods=['POST'])
def create_question():
    """Creates a new MCQ in the question database."""
    data = request.get_json() or {}
    
    question = data.get('question', '').strip()
    option_a = data.get('option_a', '').strip()
    option_b = data.get('option_b', '').strip()
    option_c = data.get('option_c', '').strip()
    option_d = data.get('option_d', '').strip()
    correct_answer = data.get('correct_answer', '').strip().upper()
    category = data.get('category', 'General').strip()
    difficulty = data.get('difficulty', 'Medium').strip()

    if not all([question, option_a, option_b, option_c, option_d, correct_answer]):
        return jsonify({"msg": "All fields except category and difficulty are required"}), 400

    if correct_answer not in ['A', 'B', 'C', 'D']:
        return jsonify({"msg": "Correct answer must be 'A', 'B', 'C', or 'D'"}), 400

    try:
        new_q = MCQ(
            question=question,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_answer=correct_answer,
            category=category,
            difficulty=difficulty
        )
        db.session.add(new_q)
        db.session.commit()
        return jsonify({"msg": "MCQ added successfully", "mcq": new_q.to_dict(include_correct=True)}), 210
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Failed to add question: {str(e)}"}), 500


@admin_bp.route('/mcqs/<int:qid>', methods=['PUT'])
def edit_question(qid):
    """Updates an existing MCQ details."""
    mcq = MCQ.query.get(qid)
    if not mcq:
        return jsonify({"msg": "MCQ not found"}), 404

    data = request.get_json() or {}
    
    mcq.question = data.get('question', mcq.question).strip()
    mcq.option_a = data.get('option_a', mcq.option_a).strip()
    mcq.option_b = data.get('option_b', mcq.option_b).strip()
    mcq.option_c = data.get('option_c', mcq.option_c).strip()
    mcq.option_d = data.get('option_d', mcq.option_d).strip()
    
    correct = data.get('correct_answer', mcq.correct_answer).strip().upper()
    if correct in ['A', 'B', 'C', 'D']:
        mcq.correct_answer = correct
    
    mcq.category = data.get('category', mcq.category).strip()
    mcq.difficulty = data.get('difficulty', mcq.difficulty).strip()

    try:
        db.session.commit()
        return jsonify({"msg": "MCQ updated successfully", "mcq": mcq.to_dict(include_correct=True)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Failed to update MCQ: {str(e)}"}), 500


@admin_bp.route('/mcqs/<int:qid>', methods=['DELETE'])
def delete_question(qid):
    """Deletes an MCQ from the database."""
    mcq = MCQ.query.get(qid)
    if not mcq:
        return jsonify({"msg": "MCQ not found"}), 404

    try:
        db.session.delete(mcq)
        db.session.commit()
        return jsonify({"msg": "MCQ deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Failed to delete MCQ: {str(e)}"}), 500


@admin_bp.route('/import', methods=['POST'])
def import_questions():
    """Bulk imports questions from a JSON array payload."""
    data = request.get_json() or []
    if not isinstance(data, list):
        return jsonify({"msg": "Request payload must be a JSON array of questions"}), 400

    imported_count = 0
    errors = []

    for idx, item in enumerate(data):
        question = item.get('question', '').strip()
        option_a = item.get('option_a', '').strip()
        option_b = item.get('option_b', '').strip()
        option_c = item.get('option_c', '').strip()
        option_d = item.get('option_d', '').strip()
        correct_answer = item.get('correct_answer', '').strip().upper()
        category = item.get('category', 'General').strip()
        difficulty = item.get('difficulty', 'Medium').strip()

        if not all([question, option_a, option_b, option_c, option_d, correct_answer]):
            errors.append(f"Row {idx+1}: Missing required fields.")
            continue

        if correct_answer not in ['A', 'B', 'C', 'D']:
            errors.append(f"Row {idx+1}: Invalid correct answer '{correct_answer}'. Must be A, B, C, or D.")
            continue

        try:
            new_q = MCQ(
                question=question,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                correct_answer=correct_answer,
                category=category,
                difficulty=difficulty
            )
            db.session.add(new_q)
            imported_count += 1
        except Exception as e:
            errors.append(f"Row {idx+1}: Database error: {str(e)}")

    if imported_count > 0:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"msg": f"Failed to save imported questions: {str(e)}"}), 500

    return jsonify({
        "msg": f"Successfully imported {imported_count} questions.",
        "errors": errors
    }), 200


@admin_bp.route('/users', methods=['GET'])
def get_users_list():
    """Returns a list of all registered users and their stats."""
    users = User.query.order_by(User.id.asc()).all()
    user_list = []
    
    for u in users:
        stats_dict = u.stats.to_dict() if u.stats else {}
        user_list.append({
            "id": u.id,
            "username": u.username,
            "streak": u.streak,
            "xp_points": u.xp_points,
            "badge": u.badge,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "stats": stats_dict
        })
        
    return jsonify(user_list), 200


@admin_bp.route('/attempts', methods=['GET'])
def get_recent_attempts():
    """Lists global recent attempts with associated student username."""
    attempts = db.session.query(Attempt, User.username)\
                         .join(User, Attempt.user_id == User.id)\
                         .order_by(Attempt.submitted_at.desc())\
                         .limit(100).all()
                         
    attempt_list = []
    for att, username in attempts:
        att_dict = att.to_dict()
        att_dict["username"] = username
        attempt_list.append(att_dict)
        
    return jsonify(attempt_list), 200


@admin_bp.route('/import-pdf', methods=['POST'])
def import_pdf_questions():
    """Extracts questions from an uploaded PDF and parses them into the database using a layout-free parser."""
    if 'file' not in request.files:
        return jsonify({"msg": "No file uploaded"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"msg": "No file selected"}), 400
        
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"msg": "Only PDF files are allowed"}), 400

    try:
        from pypdf import PdfReader
        import io
        import re

        # Read PDF text in memory
        pdf_file = io.BytesIO(file.read())
        reader = PdfReader(pdf_file)
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

        lines = full_text.split('\n')
        
        parsed_questions = []
        skipped_count = 0

        current_question = None
        current_opt_a = None
        current_opt_b = None
        current_opt_c = None
        current_opt_d = None
        current_correct = None
        current_category = None
        current_difficulty = None
        
        last_field = None # 'question', 'a', 'b', 'c', 'd'

        def save_current_mcq():
            nonlocal current_question, current_opt_a, current_opt_b, current_opt_c, current_opt_d
            nonlocal current_correct, current_category, current_difficulty, parsed_questions, skipped_count
            
            if current_question:
                q_prompt = current_question.strip()
                if q_prompt:
                    # Provide smart, layout-free defaults for missing choices and answers
                    opt_a = (current_opt_a or "Option A").strip()
                    opt_b = (current_opt_b or "Option B").strip()
                    opt_c = (current_opt_c or "Option C").strip()
                    opt_d = (current_opt_d or "Option D").strip()
                    correct = (current_correct or "A").strip().upper()
                    
                    parsed_questions.append({
                        "question": q_prompt,
                        "option_a": opt_a,
                        "option_b": opt_b,
                        "option_c": opt_c,
                        "option_d": opt_d,
                        "correct_answer": correct,
                        "category": (current_category or "Imported PDF").strip(),
                        "difficulty": (current_difficulty or "Medium").strip()
                    })
                else:
                    skipped_count += 1
                
                # Reset state
                current_question = None
                current_opt_a = None
                current_opt_b = None
                current_opt_c = None
                current_opt_d = None
                current_correct = None
                current_category = None
                current_difficulty = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 1. Match Options (e.g., A), A., (A), [A], a), a.)
            opt_a_match = re.match(r'^\s*\(?[aA][\.\)\s\]-]\s*(.+)$', line)
            opt_b_match = re.match(r'^\s*\(?[bB][\.\)\s\]-]\s*(.+)$', line)
            opt_c_match = re.match(r'^\s*\(?[cC][\.\)\s\]-]\s*(.+)$', line)
            opt_d_match = re.match(r'^\s*\(?[dD][\.\)\s\]-]\s*(.+)$', line)

            # 2. Match Question starts (e.g., Question 1:, Q1., 1.)
            q_match = re.match(r'^(?:question|q)[:\.\s-]*\d*[:\.\s-]*\s*(.+)$', line, re.IGNORECASE)
            num_match = re.match(r'^\d+[\.\s\)-]+\s*(.+)$', line)

            # 3. Match Correct Answers (e.g., Answer: A, Correct - B, Ans: C)
            ans_match = re.match(r'^(?:answer|correct|correct answer|ans)[:\.\s-]*\s*([A-D])\b', line, re.IGNORECASE)
            
            # Heuristic Search for answer inside the line (e.g., "The answer is B")
            ans_search = None
            if not ans_match:
                ans_search_match = re.search(r'\b(?:answer|ans|correct)[:\s\.-]*([A-D])\b', line, re.IGNORECASE)
                if ans_search_match:
                    ans_search = ans_search_match.group(1)

            # 4. Metadata tags (Category:, Difficulty:)
            cat_match = re.match(r'^category[:\.-]\s*(.+)$', line, re.IGNORECASE)
            diff_match = re.match(r'^difficulty[:\.-]\s*(.+)$', line, re.IGNORECASE)

            # Evaluator
            if q_match:
                save_current_mcq()
                current_question = q_match.group(1)
                last_field = 'question'
            elif num_match and not any([opt_a_match, opt_b_match, opt_c_match, opt_d_match, ans_match, cat_match, diff_match]):
                save_current_mcq()
                current_question = num_match.group(1)
                last_field = 'question'
            elif line.endswith('?') and not any([opt_a_match, opt_b_match, opt_c_match, opt_d_match, ans_match, cat_match, diff_match]):
                # If a line ends in a question mark, treat as a new question start if we already have choices active
                if current_question and (current_opt_a or current_opt_b or current_opt_c or current_opt_d):
                    save_current_mcq()
                
                if not current_question:
                    current_question = line
                else:
                    current_question += " " + line
                last_field = 'question'
            elif opt_a_match:
                current_opt_a = opt_a_match.group(1)
                last_field = 'a'
            elif opt_b_match:
                current_opt_b = opt_b_match.group(1)
                last_field = 'b'
            elif opt_c_match:
                current_opt_c = opt_c_match.group(1)
                last_field = 'c'
            elif opt_d_match:
                current_opt_d = opt_d_match.group(1)
                last_field = 'd'
            elif ans_match:
                current_correct = ans_match.group(1)
                last_field = None
            elif ans_search:
                current_correct = ans_search
                last_field = None
            elif cat_match:
                current_category = cat_match.group(1)
                last_field = None
            elif diff_match:
                diff_val = diff_match.group(1).strip()
                if diff_val.lower() in ['easy', 'medium', 'hard']:
                    current_difficulty = diff_val.capitalize()
                last_field = None
            else:
                # Text continuation/multi-line wrapping
                if last_field == 'question' and current_question:
                    current_question += " " + line
                elif last_field == 'a' and current_opt_a:
                    current_opt_a += " " + line
                elif last_field == 'b' and current_opt_b:
                    current_opt_b += " " + line
                elif last_field == 'c' and current_opt_c:
                    current_opt_c += " " + line
                elif last_field == 'd' and current_opt_d:
                    current_opt_d += " " + line

        # Save trailing final question block
        save_current_mcq()

        if len(parsed_questions) == 0:
            return jsonify({"msg": "Could not parse any valid questions. Ensure the PDF contains readable text.", "skipped": skipped_count}), 400

        # Bulk write to database
        imported_count = 0
        for q in parsed_questions:
            new_q = MCQ(
                question=q["question"],
                option_a=q["option_a"],
                option_b=q["option_b"],
                option_c=q["option_c"],
                option_d=q["option_d"],
                correct_answer=q["correct_answer"],
                category=q["category"],
                difficulty=q["difficulty"]
            )
            db.session.add(new_q)
            imported_count += 1
            
        db.session.commit()
        return jsonify({
            "msg": f"Successfully parsed and imported {imported_count} questions from PDF.",
            "skipped": skipped_count
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"Failed to process PDF: {str(e)}"}), 500
