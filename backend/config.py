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
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
