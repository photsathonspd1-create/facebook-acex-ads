from flask import Flask, render_template, send_from_directory, jsonify, request, session
import os
import sqlite3
import models

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'SOVEREIGN_KEY_LOTTO'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory('static/assets', path)

# --- REAL AUTH API ---

@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    # Auto-login the first user for convenience, or return null if none
    with models.get_db() as db:
        user = db.execute("SELECT * FROM users LIMIT 1").fetchone()
        if user:
            return jsonify({"user": {"id": user['id'], "name": user['name'], "email": user['email'], "role": "admin"}})
    return jsonify({"user": None})

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    try:
        with models.get_db() as db:
            db.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
                       (data['email'], data['password'], data['name']))
            db.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --- REAL SETTINGS API (For FB Token) ---

@app.route('/api/fb/token', methods=['POST'])
def save_token():
    data = request.json
    token = data.get('token')
    with models.get_db() as db:
        db.execute("UPDATE users SET fb_token = ? WHERE id = (SELECT id FROM users LIMIT 1)", (token,))
        db.commit()
    return jsonify({"ok": True})

# --- MOCK REMAINING (To prevent UI errors) ---
@app.route('/api/announcements/active', methods=['GET'])
def active_announcements(): return jsonify([])

@app.route('/api/fb/ad-accounts', methods=['GET'])
def fb_accounts():
    with models.get_db() as db:
        user = db.execute("SELECT fb_token FROM users LIMIT 1").fetchone()
        if not user or not user['fb_token']:
            return jsonify({"accounts": [], "error": "Please enter FB Token in Settings"})
    return jsonify({"accounts": [{"id": "act_123", "name": "Real Account Ready", "status": "ACTIVE"}]})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)
