import os
from datetime import timedelta

class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    
    # SQLAlchemy Configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_TYPE = os.getenv('SESSION_TYPE', 'filesystem')  # Default to filesystem if Redis is not configured
    if SESSION_TYPE == 'redis':
        SESSION_REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
        SESSION_REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    
    # Cache Configuration
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'SimpleCache')  # Default to SimpleCache if Redis is not configured
    if CACHE_TYPE == 'redis':
        CACHE_REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
        CACHE_REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    CACHE_DEFAULT_TIMEOUT = 300

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "users.db")}'
    SQLALCHEMY_BINDS = {
        'leads': os.getenv('DATABASE_URL')
    }

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('USERS_DATABASE_URL')
    SQLALCHEMY_BINDS = {
        'leads': os.getenv('LEADS_DATABASE_URL')
    }
    
    # Production specific settings
    PREFERRED_URL_SCHEME = 'https'
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True