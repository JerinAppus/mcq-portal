import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class for the Flask backend."""
    # General Config
    SECRET_KEY = os.getenv("SECRET_KEY", "default-fallback-secret-key-12345")
    DEBUG = os.getenv("FLASK_ENV") == "development"

    # Database Config
    # If DATABASE_URL is not found, fallback to local SQLite database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///mcq_battle.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT Config
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "default-fallback-jwt-secret-key-67890")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=1)
    
    # Cookie-based secure JWT with CSRF Double-Submit token protection
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_COOKIE_SECURE = False  # Set to True in production (requires HTTPS)
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_CSRF_METHODS = ["POST", "PUT", "PATCH", "DELETE"]  # GET requests are exempt
    JWT_CSRF_IN_HEADERS = True
    JWT_ACCESS_COOKIE_NAME = "access_token_cookie"
    JWT_ACCESS_CSRF_COOKIE_NAME = "csrf_access_token"
    JWT_ACCESS_CSRF_HEADER_NAME = "X-CSRF-Token"
