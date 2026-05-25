from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """User representation representing registered students."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    streak = db.Column(db.Integer, default=0, nullable=False)
    xp_points = db.Column(db.Integer, default=0, nullable=False)
    badge = db.Column(db.String(50), default='Bronze', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    attempts = db.relationship('Attempt', backref='user', lazy=True, cascade="all, delete-orphan")
    stats = db.relationship('Stats', backref='user', uselist=False, lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        """Hashes the password and saves it."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Serializes user fields for JSON API consumption."""
        return {
            "id": self.id,
            "username": self.username,
            "streak": self.streak,
            "xp_points": self.xp_points,
            "badge": self.badge,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class MCQ(db.Model):
    """Model for Multiple Choice Questions."""
    __tablename__ = 'mcqs'

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.Text, nullable=False)
    option_b = db.Column(db.Text, nullable=False)
    option_c = db.Column(db.Text, nullable=False)
    option_d = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False) # 'A', 'B', 'C', or 'D'
    category = db.Column(db.String(100), default='General', nullable=False)
    difficulty = db.Column(db.String(50), default='Medium', nullable=False)

    def to_dict(self, include_correct=False):
        """Serializes MCQ fields. Excludes correct answer for students during quiz."""
        data = {
            "id": self.id,
            "question": self.question,
            "option_a": self.option_a,
            "option_b": self.option_b,
            "option_c": self.option_c,
            "option_d": self.option_d,
            "category": self.category,
            "difficulty": self.difficulty
        }
        if include_correct:
            data["correct_answer"] = self.correct_answer
        return data


class Attempt(db.Model):
    """Represents a completed quiz attempt by a student."""
    __tablename__ = 'attempts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    score = db.Column(db.Integer, nullable=False) # Number of correct answers
    total_questions = db.Column(db.Integer, nullable=False)
    accuracy = db.Column(db.Float, nullable=False) # (score / total_questions) * 100
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Serializes attempt data."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "score": self.score,
            "total_questions": self.total_questions,
            "accuracy": round(self.accuracy, 2),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None
        }


class Stats(db.Model):
    """Aggregated statistics for each user."""
    __tablename__ = 'stats'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    highest_score = db.Column(db.Integer, default=0, nullable=False)
    average_score = db.Column(db.Float, default=0.0, nullable=False)
    total_attempts = db.Column(db.Integer, default=0, nullable=False)
    win_ratio = db.Column(db.Float, default=0.0, nullable=False) # (total correct answers / total attempted questions) * 100
    current_streak = db.Column(db.Integer, default=0, nullable=False)

    def to_dict(self):
        """Serializes aggregate stats data."""
        return {
            "user_id": self.user_id,
            "highest_score": self.highest_score,
            "average_score": round(self.average_score, 2),
            "total_attempts": self.total_attempts,
            "win_ratio": round(self.win_ratio, 2),
            "current_streak": self.current_streak
        }
