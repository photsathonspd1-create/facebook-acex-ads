#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

# Create venv if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q -r requirements.txt

# Copy .env if missing
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env from .env.example..."
    cp .env.example .env
    # Generate a random secret key
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/change-me-to-a-random-string/$SECRET/" .env
    ENC_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/^ENCRYPTION_KEY=$/ENCRYPTION_KEY=$ENC_KEY/" .env
    echo "✅ .env created with random keys"
fi

echo ""
echo "🚀 Starting Acex Ads..."
echo "   Open http://localhost:${PORT:-8080} in your browser"
echo ""

cd app
python3 app.py
