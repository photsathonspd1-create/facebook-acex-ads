#!/bin/bash
# Acex Ads — Production startup script
# Uses gunicorn if available, falls back to Flask dev server

set -e

cd "$(dirname "$0")"

# Initialize database
python -c "import models; print('✅ Database initialized')"

if command -v gunicorn &> /dev/null; then
    echo "🚀 Starting with Gunicorn (production mode)..."
    exec gunicorn -c gunicorn.conf.py "app:app"
else
    echo "⚠️  Gunicorn not found. Starting Flask dev server..."
    echo "   Install gunicorn for production: pip install gunicorn"
    exec python app.py
fi
