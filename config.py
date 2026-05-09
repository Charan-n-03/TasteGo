import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DB_URI')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'tastego-secret-key-2026')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
