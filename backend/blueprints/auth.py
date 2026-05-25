from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from backend.models import db, User, Stats

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Registers a new user, hashes password, and creates standard stats."""
    data = request.get_json() or {}
    
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    # Input sanitization and validations
    if not username or not password:
        return jsonify({"msg": "Username and password are required"}), 400

    if len(username) < 3 or len(username) > 30:
        return jsonify({"msg": "Username must be between 3 and 30 characters"}), 400

    if len(password) < 6:
        return jsonify({"msg": "Password must be at least 6 characters long"}), 400

    # SQL Injection protection & duplicate check
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"msg": "Username already exists"}), 409

    try:
        # Create User
        new_user = User(username=username)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.flush() # Populate new_user.id for stats foreign key

        # Create user Stats
        user_stats = Stats(
            user_id=new_user.id,
            highest_score=0,
            average_score=0.0,
            total_attempts=0,
            win_ratio=0.0,
            current_streak=0
        )
        db.session.add(user_stats)
        db.session.commit()

        return jsonify({"msg": "Registration successful. You can now login.", "user": new_user.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"msg": f"An error occurred: {str(e)}"}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Logs in user and returns a stateless JWT access token."""
    data = request.get_json() or {}
    
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({"msg": "Username and password are required"}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({"msg": "Invalid username or password"}), 401

    # Check streak reset on login in case they missed days
    # Wait, streak is naturally recalculated on quiz submit, but keeping it updated is great!
    
    # Generate token
    # Flask-JWT-Extended stores the identity as a string
    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        "msg": "Login successful",
        "access_token": access_token,
        "user": user.to_dict()
    }), 200


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Gets details of the logged in user."""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))
    
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    return jsonify({
        "user": user.to_dict(),
        "stats": user.stats.to_dict() if user.stats else None
    }), 200


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logs out user (stateless, simply returns success for client cleanup)."""
    return jsonify({"msg": "Logged out successfully"}), 200
