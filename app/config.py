"""
Configuration management via environment variables.
Loads from .env file if present, falls back to environment.
"""
import os
import secrets
import logging

logger = logging.getLogger(__name__)

# Load .env file — check both CWD and the project root (one level up from app/)
_env_paths = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'),
    '.env',
]
for _env_path in _env_paths:
    try:
        with open(_env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ.setdefault(key.strip(), val.strip())
        break  # Stop after first .env found
    except FileNotFoundError:
        continue

# Flask — generate a secure random key if not explicitly configured
_configured_secret = os.environ.get('SECRET_KEY', '')
if not _configured_secret or _configured_secret == 'change-me-in-production':
    SECRET_KEY = secrets.token_hex(32)
    logger.warning(
        "SECRET_KEY not configured — using auto-generated key. "
        "Sessions will NOT persist across restarts. "
        "Set SECRET_KEY in .env for production."
    )
else:
    SECRET_KEY = _configured_secret

DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
PORT = int(os.environ.get('PORT', 8080))
HOST = os.environ.get('HOST', '0.0.0.0')

# Database
DB_PATH = os.environ.get('DB_PATH', 'scaler.db')

# Facebook
FB_API_VERSION = os.environ.get('FB_API_VERSION', 'v19.0')
FB_APP_ID = os.environ.get('FB_APP_ID', '')
FB_APP_SECRET = os.environ.get('FB_APP_SECRET', '')
FB_REDIRECT_URI = os.environ.get('FB_REDIRECT_URI', '')

# CORS
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')

# OpenAI
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

# Logging
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = os.environ.get('LOG_FILE', 'scaler.log')
