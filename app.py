"""
Acex Ads — Flask Backend
All 50+ API endpoints with proper error handling, logging, and input validation.
"""
from flask import Flask, render_template, send_from_directory, jsonify, request, session, Response
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import sqlite3
import logging
import models
import config
import ai_service
import scheduler
import migrations
from datetime import datetime, timedelta
from functools import wraps
from math import sqrt

# ─── Logging Setup ───
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.LOG_FILE, encoding='utf-8'),
    ]
)
logger = logging.getLogger('scaler')

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = config.SECRET_KEY

# ─── Rate Limiting (in-memory) ───

_rate_store = {}  # key -> [timestamps]

def rate_limit(max_calls, window_seconds):
    """Decorator: rate limit by IP address."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            key = f"{request.remote_addr}:{f.__name__}"
            now = datetime.utcnow().timestamp()
            window_start = now - window_seconds

            if key not in _rate_store:
                _rate_store[key] = []

            # Clean old entries
            _rate_store[key] = [t for t in _rate_store[key] if t > window_start]

            if len(_rate_store[key]) >= max_calls:
                retry_after = int(_rate_store[key][0] + window_seconds - now) + 1
                return jsonify({"error": "Too many requests", "retry_after": retry_after}), 429

            _rate_store[key].append(now)
            return f(*args, **kwargs)
        return decorated
    return decorator

# ─── CORS ───

@app.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses."""
    cors_origins = os.environ.get('CORS_ORIGINS', '*')
    origin = request.headers.get('Origin', '')
    if cors_origins == '*':
        response.headers['Access-Control-Allow-Origin'] = '*'
    elif origin in cors_origins.split(','):
        response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response

@app.before_request
def handle_preflight():
    """Handle CORS preflight OPTIONS requests."""
    if request.method == 'OPTIONS':
        return '', 204

# ─── Helpers ───

def get_current_user():
    """Get current logged-in user from session or auto-login first user."""
    try:
        # BYPASS LOGIN FOR USER
        with models.db_conn() as db:
            row = db.execute("SELECT * FROM users WHERE email = 'admin@test.com'").fetchone()
            if row:
                return dict(row)
        
        user_id = session.get('user_id')
        with models.db_conn() as db:
            row = db.execute("SELECT * FROM users LIMIT 1").fetchone()
            if row:
                return dict(row)
    except Exception as e:
        logger.error(f"get_current_user error: {e}")
    return None

def get_fb_token():
    user = get_current_user()
    if user and user.get('fb_token'):
        return user['fb_token']
    return None

def fb_api(endpoint, params=None, method='GET', data=None):
    """Call Facebook Marketing API."""
    token = get_fb_token()
    if not token:
        return {"error": "No Facebook token configured. Go to Settings."}
    import requests as req
    url = f"https://graph.facebook.com/{config.FB_API_VERSION}/{endpoint}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        if method == 'GET':
            resp = req.get(url, params=params or {}, headers=headers, timeout=15)
        elif method == 'POST':
            resp = req.post(url, json=data or {}, headers=headers, timeout=15)
        elif method == 'PUT':
            resp = req.put(url, json=data or {}, headers=headers, timeout=15)
        elif method == 'DELETE':
            resp = req.delete(url, headers=headers, timeout=15)
        else:
            return {"error": f"Unsupported method: {method}"}
        return resp.json()
    except req.exceptions.Timeout:
        return {"error": "Facebook API request timed out"}
    except Exception as e:
        logger.error(f"fb_api error for {endpoint}: {e}")
        return {"error": str(e)}

def require_auth(f):
    """Decorator: require login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Not authenticated"}), 401
        return f(user, *args, **kwargs)
    return decorated

def safe_int(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default

def safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

# ─── Frontend ───

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/guide')
def guide():
    return render_template('guide.html')

@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory(os.path.join(app.root_path, 'static', 'assets'), path)

# SPA catch-all: serve index.html for all non-API, non-static routes
# This allows React Router to handle client-side routing
@app.route('/<path:path>')
def spa_catchall(path):
    # Don't intercept API routes
    if path.startswith('api/'):
        return jsonify({"error": "API route not found"}), 404
    # For everything else, serve index.html (React handles the rest)
    return render_template('index.html')

# ─── Auth API ───

@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    try:
        user = get_current_user()
        if user:
            return jsonify({"user": {
                "id": user['id'],
                "name": user['name'],
                "email": user['email'],
                "role": user.get('role', 'admin')
            }})
        return jsonify({"user": None})
    except Exception as e:
        logger.error(f"auth_me error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.json
        if not data or not data.get('email') or not data.get('password') or not data.get('name'):
            return jsonify({"error": "Missing required fields (email, password, name)"}), 400
        if len(data['password']) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        if '@' not in data['email']:
            return jsonify({"error": "Invalid email format"}), 400
        hashed = generate_password_hash(data['password'])
        with models.db_conn() as db:
            db.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
                       (data['email'], hashed, data['name']))
        return jsonify({"ok": True})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already registered"}), 400
    except Exception as e:
        logger.error(f"register error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
@rate_limit(5, 60)
def login():
    try:
        data = request.json
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({"error": "Missing email or password"}), 400
        with models.db_conn() as db:
            row = db.execute("SELECT * FROM users WHERE email = ?",
                              (data['email'],)).fetchone()
        if row:
            user = dict(row)
            password_valid = False
            # werkzeug hashed passwords contain ':' (e.g. scrypt:..., pbkdf2:...)
            if ':' in user['password'] and len(user['password']) > 20:
                password_valid = check_password_hash(user['password'], data['password'])
            else:
                # Legacy plaintext password — check and migrate
                if user['password'] == data['password']:
                    password_valid = True
                    # Migrate to hashed password
                    hashed = generate_password_hash(data['password'])
                    with models.db_conn() as db:
                        db.execute("UPDATE users SET password = ? WHERE id = ?",
                                   (hashed, user['id']))
            if password_valid:
                session['user_id'] = user['id']
                return jsonify({"ok": True, "user": {
                    "id": user['id'],
                    "name": user['name'],
                    "email": user['email'],
                    "role": user.get('role', 'admin')
                }})
        return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        logger.error(f"login error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({"ok": True})

@app.route('/api/auth/facebook', methods=['GET'])
def auth_facebook():
    """Initiate Facebook OAuth2 flow."""
    fb_app_id = config.FB_APP_ID
    fb_redirect_uri = config.FB_REDIRECT_URI
    if not fb_app_id or not fb_redirect_uri:
        return jsonify({"error": "Facebook OAuth not configured"}), 501
    scope = 'email,public_profile,ads_management,ads_read'
    fb_auth_url = (
        f"https://www.facebook.com/{config.FB_API_VERSION}/dialog/oauth?"
        f"client_id={fb_app_id}&redirect_uri={fb_redirect_uri}&scope={scope}&response_type=code"
    )
    return jsonify({"redirect_url": fb_auth_url})

@app.route('/api/auth/facebook/callback', methods=['GET'])
def auth_facebook_callback():
    """Handle Facebook OAuth2 callback."""
    try:
        code = request.args.get('code')
        if not code:
            return jsonify({"error": "Missing authorization code"}), 400

        fb_app_id = os.environ.get('FB_APP_ID', '')
        fb_app_secret = os.environ.get('FB_APP_SECRET', '')
        fb_redirect_uri = os.environ.get('FB_REDIRECT_URI', '')

        if not fb_app_id or not fb_app_secret:
            return jsonify({"error": "Facebook OAuth not configured"}), 500

        import requests as req

        # Exchange code for access token
        token_resp = req.get(
            f"https://graph.facebook.com/{config.FB_API_VERSION}/oauth/access_token",
            params={
                'client_id': fb_app_id,
                'client_secret': fb_app_secret,
                'redirect_uri': fb_redirect_uri,
                'code': code,
            },
            timeout=15,
        )
        token_data = token_resp.json()
        if 'error' in token_data:
            return jsonify({"error": f"Token exchange failed: {token_data['error'].get('message', 'Unknown error')}"}), 400

        access_token = token_data.get('access_token')
        if not access_token:
            return jsonify({"error": "No access token received"}), 400

        # Get user info from Facebook
        user_resp = req.get(
            f"https://graph.facebook.com/{config.FB_API_VERSION}/me",
            params={'fields': 'id,name,email', 'access_token': access_token},
            timeout=15,
        )
        fb_user = user_resp.json()
        if 'error' in fb_user:
            return jsonify({"error": f"Failed to get user info: {fb_user['error'].get('message', '')}"}), 400

        fb_email = fb_user.get('email', f"fb_{fb_user['id']}@facebook.local")
        fb_name = fb_user.get('name', 'Facebook User')

        # Create or find user
        with models.db_conn() as db:
            existing = db.execute("SELECT * FROM users WHERE email = ?", (fb_email,)).fetchone()
            if existing:
                user_id = existing['id']
                db.execute("UPDATE users SET fb_token = ? WHERE id = ?", (access_token, user_id))
            else:
                cursor = db.execute(
                    "INSERT INTO users (email, password, name, fb_token) VALUES (?, ?, ?, ?)",
                    (fb_email, generate_password_hash(os.urandom(16).hex()), fb_name, access_token)
                )
                user_id = cursor.lastrowid

        session['user_id'] = user_id
        return jsonify({"ok": True, "user": {"id": user_id, "name": fb_name, "email": fb_email}})
    except Exception as e:
        logger.error(f"auth_facebook_callback error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Settings API ───

@app.route('/api/fb/token', methods=['POST'])
@require_auth
def save_token(user):
    try:
        data = request.json
        token = (data or {}).get('token', '')
        if not isinstance(token, str):
            return jsonify({"error": "Token must be a string"}), 400
        with models.db_conn() as db:
            db.execute("UPDATE users SET fb_token = ? WHERE id = ?", (token, user['id']))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"save_token error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Facebook API ───

@app.route('/api/fb/ad-accounts', methods=['GET'])
@require_auth
def fb_accounts(user):
    try:
        result = fb_api('me/adaccounts', params={
            'fields': 'id,name,account_status,currency,timezone_name,business_name',
            'limit': 500,
        })
        if 'error' in result and 'data' not in result:
            return jsonify({"accounts": [], "error": result['error']})
        status_map = {1: 'ACTIVE', 2: 'DISABLED', 3: 'UNSETTLED', 7: 'PENDING'}
        accounts = []
        for acc in result.get('data', []):
            accounts.append({
                "id": acc['id'],
                "name": acc.get('name', ''),
                "status": status_map.get(acc.get('account_status'), 'UNKNOWN'),
                "currency": acc.get('currency', 'USD'),
                "timezone": acc.get('timezone_name', ''),
                "business": acc.get('business_name', ''),
            })
        return jsonify({"accounts": accounts})
    except Exception as e:
        logger.error(f"fb_accounts error: {e}")
        return jsonify({"accounts": [], "error": str(e)}), 500

@app.route('/api/fb/campaigns', methods=['GET'])
@require_auth
def fb_campaigns(user):
    try:
        account_id = request.args.get('account_id')
        if not account_id:
            accs = fb_api('me/adaccounts', params={'fields': 'id'})
            data = accs.get('data', [])
            if not data:
                return jsonify({"campaigns": [], "error": "No ad accounts found"})
            account_id = data[0]['id']
        result = fb_api(f'{account_id}/campaigns', params={
            'fields': 'id,name,status,objective,daily_budget,lifetime_budget,created_time,updated_time,stop_times',
            'limit': 500,
        })
        if 'error' in result and 'data' not in result:
            return jsonify({"campaigns": [], "error": result['error']})
        campaigns = []
        for c in result.get('data', []):
            campaigns.append({
                "id": c['id'],
                "name": c.get('name', ''),
                "status": c.get('status', 'UNKNOWN'),
                "objective": c.get('objective', ''),
                "daily_budget": safe_float(c.get('daily_budget')) / 100 if c.get('daily_budget') else None,
                "lifetime_budget": safe_float(c.get('lifetime_budget')) / 100 if c.get('lifetime_budget') else None,
                "created_time": c.get('created_time', ''),
                "updated_time": c.get('updated_time', ''),
            })
        return jsonify({"campaigns": campaigns})
    except Exception as e:
        logger.error(f"fb_campaigns error: {e}")
        return jsonify({"campaigns": [], "error": str(e)}), 500

@app.route('/api/fb/campaigns/<campaign_id>/status', methods=['PUT'])
@require_auth
def update_campaign_status(user, campaign_id):
    try:
        data = request.json
        if not data or not data.get('status'):
            return jsonify({"error": "Status required (ACTIVE or PAUSED)"}), 400
        status = data['status']
        if status not in ('ACTIVE', 'PAUSED', 'ARCHIVED', 'DELETED'):
            return jsonify({"error": "Invalid status"}), 400
        result = fb_api(campaign_id, method='POST', data={'status': status})
        if 'error' in result:
            return jsonify(result), 400
        with models.db_conn() as db:
            db.execute("""INSERT INTO bot_actions (user_id, action_type, target_type, target_id, target_name, details)
                          VALUES (?, ?, ?, ?, ?, ?)""",
                       (user['id'], 'campaign_status_change', 'campaign', campaign_id,
                        campaign_id, json.dumps({"new_status": status})))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"update_campaign_status error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/fb/campaigns/<campaign_id>/budget', methods=['PUT'])
@require_auth
def update_campaign_budget(user, campaign_id):
    try:
        data = request.json
        budget = (data or {}).get('budget')
        budget_type = (data or {}).get('type', 'daily')
        if budget is None:
            return jsonify({"error": "Budget required"}), 400
        budget = safe_float(budget)
        if budget <= 0:
            return jsonify({"error": "Budget must be positive"}), 400
        if budget_type not in ('daily', 'lifetime'):
            return jsonify({"error": "Type must be 'daily' or 'lifetime'"}), 400
        field = 'daily_budget' if budget_type == 'daily' else 'lifetime_budget'
        result = fb_api(campaign_id, method='POST', data={field: str(int(budget * 100))})
        if 'error' in result:
            return jsonify(result), 400
        with models.db_conn() as db:
            db.execute("""INSERT INTO bot_actions (user_id, action_type, target_type, target_id, target_name, details)
                          VALUES (?, ?, ?, ?, ?, ?)""",
                       (user['id'], 'budget_change', 'campaign', campaign_id,
                        campaign_id, json.dumps({"budget": budget, "type": budget_type})))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"update_campaign_budget error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/fb/adsets', methods=['GET'])
@require_auth
def fb_adsets(user):
    try:
        account_id = request.args.get('account_id')
        if not account_id:
            accs = fb_api('me/adaccounts', params={'fields': 'id'})
            data = accs.get('data', [])
            if not data:
                return jsonify({"adsets": []})
            account_id = data[0]['id']
        result = fb_api(f'{account_id}/adsets', params={
            'fields': 'id,name,status,campaign_id,daily_budget,bid_amount,targeting,created_time',
            'limit': 500,
        })
        if 'error' in result and 'data' not in result:
            return jsonify({"adsets": [], "error": result['error']})
        adsets = []
        for a in result.get('data', []):
            adsets.append({
                "id": a['id'],
                "name": a.get('name', ''),
                "status": a.get('status', 'UNKNOWN'),
                "campaign_id": a.get('campaign_id', ''),
                "daily_budget": safe_float(a.get('daily_budget')) / 100 if a.get('daily_budget') else None,
                "bid_amount": a.get('bid_amount'),
                "targeting": a.get('targeting', {}),
                "created_time": a.get('created_time', ''),
            })
        return jsonify({"adsets": adsets})
    except Exception as e:
        logger.error(f"fb_adsets error: {e}")
        return jsonify({"adsets": [], "error": str(e)}), 500

@app.route('/api/fb/ads', methods=['GET'])
@require_auth
def fb_ads(user):
    try:
        account_id = request.args.get('account_id')
        if not account_id:
            accs = fb_api('me/adaccounts', params={'fields': 'id'})
            data = accs.get('data', [])
            if not data:
                return jsonify({"ads": []})
            account_id = data[0]['id']
        result = fb_api(f'{account_id}/ads', params={
            'fields': 'id,name,status,adset_id,creative,created_time',
            'limit': 500,
        })
        if 'error' in result and 'data' not in result:
            return jsonify({"ads": [], "error": result['error']})
        ads = []
        for a in result.get('data', []):
            ads.append({
                "id": a['id'],
                "name": a.get('name', ''),
                "status": a.get('status', 'UNKNOWN'),
                "adset_id": a.get('adset_id', ''),
                "creative": a.get('creative', {}),
                "created_time": a.get('created_time', ''),
            })
        return jsonify({"ads": ads})
    except Exception as e:
        logger.error(f"fb_ads error: {e}")
        return jsonify({"ads": [], "error": str(e)}), 500

@app.route('/api/fb/ads/<ad_id>/creative', methods=['PUT'])
@require_auth
def update_ad_creative(user, ad_id):
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Creative data required"}), 400
        result = fb_api(ad_id, method='POST', data={'creative': data})
        if 'error' in result:
            return jsonify(result), 400
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"update_ad_creative error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/fb/insights', methods=['GET'])
@require_auth
def fb_insights(user):
    try:
        account_id = request.args.get('account_id')
        date_preset = request.args.get('date_preset', 'last_7d')
        level = request.args.get('level', 'campaign')
        time_increment = request.args.get('time_increment')
        if not account_id:
            accs = fb_api('me/adaccounts', params={'fields': 'id'})
            data = accs.get('data', [])
            if not data:
                return jsonify({"insights": []})
            account_id = data[0]['id']
        params = {
            'fields': 'impressions,clicks,spend,reach,ctr,cpc,cpm,actions,cost_per_action_type',
            'date_preset': date_preset,
            'level': level,
            'limit': 500,
        }
        if time_increment:
            params['time_increment'] = time_increment
        result = fb_api(f'{account_id}/insights', params=params)
        if 'error' in result and 'data' not in result:
            return jsonify({"insights": [], "error": result['error']})
        insights = []
        for row in result.get('data', []):
            actions = {}
            for a in row.get('actions', []):
                actions[a.get('action_type', '')] = a.get('value', 0)
            insights.append({
                "impressions": safe_int(row.get('impressions')),
                "clicks": safe_int(row.get('clicks')),
                "spend": safe_float(row.get('spend')),
                "reach": safe_int(row.get('reach')),
                "ctr": safe_float(row.get('ctr')),
                "cpc": safe_float(row.get('cpc')),
                "cpm": safe_float(row.get('cpm')),
                "actions": actions,
                "campaign_id": row.get('campaign_id', ''),
                "campaign_name": row.get('campaign_name', ''),
                "adset_id": row.get('adset_id', ''),
                "ad_id": row.get('ad_id', ''),
                "date_start": row.get('date_start', ''),
                "date_stop": row.get('date_stop', ''),
            })
        return jsonify({"insights": insights})
    except Exception as e:
        logger.error(f"fb_insights error: {e}")
        return jsonify({"insights": [], "error": str(e)}), 500

@app.route('/api/fb/insights/compare', methods=['GET'])
@require_auth
def fb_insights_compare(user):
    try:
        account_id = request.args.get('account_id')
        if not account_id:
            accs = fb_api('me/adaccounts', params={'fields': 'id'})
            data = accs.get('data', [])
            if not data:
                return jsonify({"current": [], "previous": []})
            account_id = data[0]['id']
        current = fb_api(f'{account_id}/insights', params={
            'fields': 'impressions,clicks,spend,reach,ctr,cpc,cpm',
            'date_preset': 'last_7d',
            'level': 'campaign',
        })
        previous = fb_api(f'{account_id}/insights', params={
            'fields': 'impressions,clicks,spend,reach,ctr,cpc,cpm',
            'date_preset': 'last_14d',
            'time_increment': 7,
            'level': 'campaign',
        })
        return jsonify({
            "current": current.get('data', []),
            "previous": previous.get('data', []),
        })
    except Exception as e:
        logger.error(f"fb_insights_compare error: {e}")
        return jsonify({"current": [], "previous": [], "error": str(e)}), 500

@app.route('/api/fb/summary', methods=['GET'])
@require_auth
def fb_summary(user):
    try:
        account_id = request.args.get('account_id')
        if not account_id:
            accs = fb_api('me/adaccounts', params={'fields': 'id'})
            data = accs.get('data', [])
            if not data:
                return jsonify({"summary": {}})
            account_id = data[0]['id']
        result = fb_api(f'{account_id}/insights', params={
            'fields': 'impressions,clicks,spend,reach,ctr,cpc,cpm,actions',
            'date_preset': 'last_7d',
            'level': 'account',
        })
        data = result.get('data', [])
        if data:
            row = data[0]
            actions = {}
            for a in row.get('actions', []):
                actions[a.get('action_type', '')] = a.get('value', 0)
            return jsonify({"summary": {
                "impressions": safe_int(row.get('impressions')),
                "clicks": safe_int(row.get('clicks')),
                "spend": safe_float(row.get('spend')),
                "reach": safe_int(row.get('reach')),
                "ctr": safe_float(row.get('ctr')),
                "cpc": safe_float(row.get('cpc')),
                "cpm": safe_float(row.get('cpm')),
                "actions": actions,
            }})
        return jsonify({"summary": {}})
    except Exception as e:
        logger.error(f"fb_summary error: {e}")
        return jsonify({"summary": {}, "error": str(e)}), 500

@app.route('/api/fb/activity', methods=['GET'])
@require_auth
def fb_activity(user):
    try:
        limit = request.args.get('limit', 50, type=int)
        limit = min(max(limit, 1), 500)
        with models.db_conn() as db:
            rows = db.execute(
                "SELECT * FROM bot_actions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user['id'], limit)
            ).fetchall()
        actions = []
        for r in rows:
            actions.append({
                "id": r['id'],
                "type": r['action_type'],
                "target_type": r['target_type'],
                "target_id": r['target_id'],
                "target_name": r['target_name'],
                "details": json.loads(r['details']) if r['details'] else {},
                "undoable": bool(r['undoable']) and not bool(r['undone']),
                "created_at": r['created_at'],
            })
        return jsonify({"activity": actions})
    except Exception as e:
        logger.error(f"fb_activity error: {e}")
        return jsonify({"activity": [], "error": str(e)}), 500

@app.route('/api/fb/audience', methods=['GET'])
@require_auth
def fb_audience(user):
    try:
        account_id = request.args.get('account_id')
        if not account_id:
            accs = fb_api('me/adaccounts', params={'fields': 'id'})
            data = accs.get('data', [])
            if not data:
                return jsonify({"audience": {}})
            account_id = data[0]['id']
        result = fb_api(f'{account_id}/reachestimate', params={
            'targeting_spec': json.dumps({"geo_locations": {"countries": ["TH"]}}),
        })
        return jsonify({"audience": result})
    except Exception as e:
        logger.error(f"fb_audience error: {e}")
        return jsonify({"audience": {}, "error": str(e)}), 500

# ─── Feature 1: Smart Scaling Intelligence + Kill Switch ───

@app.route('/api/scaling/config', methods=['POST'])
@require_auth
def save_scaling_config(user):
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Config data required"}), 400
        max_increase = safe_float(data.get('max_budget_increase_pct'), 30)
        min_roas = safe_float(data.get('min_roas_threshold'), 2.0)
        lookback = safe_int(data.get('lookback_days'), 7)
        kill_loss = safe_float(data.get('kill_loss_threshold'), 500)
        account_id = data.get('account_id', '')

        if max_increase <= 0 or max_increase > 200:
            return jsonify({"error": "max_budget_increase_pct must be 0-200"}), 400
        if min_roas < 0:
            return jsonify({"error": "min_roas_threshold must be >= 0"}), 400
        if lookback < 1 or lookback > 90:
            return jsonify({"error": "lookback_days must be 1-90"}), 400

        with models.db_conn() as db:
            existing = db.execute("SELECT id FROM scaling_configs WHERE user_id = ? AND account_id = ?",
                                  (user['id'], account_id)).fetchone()
            if existing:
                db.execute("""UPDATE scaling_configs SET max_budget_increase_pct=?, min_roas_threshold=?,
                             lookback_days=?, kill_loss_threshold=?, updated_at=datetime('now')
                             WHERE id=?""",
                           (max_increase, min_roas, lookback, kill_loss, existing['id']))
            else:
                db.execute("""INSERT INTO scaling_configs
                             (user_id, account_id, max_budget_increase_pct, min_roas_threshold, lookback_days, kill_loss_threshold)
                             VALUES (?, ?, ?, ?, ?, ?)""",
                           (user['id'], account_id, max_increase, min_roas, lookback, kill_loss))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"save_scaling_config error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scaling/config', methods=['GET'])
@require_auth
def get_scaling_config(user):
    try:
        account_id = request.args.get('account_id', '')
        with models.db_conn() as db:
            row = db.execute("SELECT * FROM scaling_configs WHERE user_id = ? AND account_id = ?",
                             (user['id'], account_id)).fetchone()
        if row:
            return jsonify({"config": {
                "max_budget_increase_pct": row['max_budget_increase_pct'],
                "min_roas_threshold": row['min_roas_threshold'],
                "lookback_days": row['lookback_days'],
                "kill_loss_threshold": row['kill_loss_threshold'],
                "account_id": row['account_id'],
            }})
        return jsonify({"config": {
            "max_budget_increase_pct": 30,
            "min_roas_threshold": 2.0,
            "lookback_days": 7,
            "kill_loss_threshold": 500,
            "account_id": "",
        }})
    except Exception as e:
        logger.error(f"get_scaling_config error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scaling/analyze', methods=['POST'])
@require_auth
def analyze_scaling(user):
    try:
        data = request.json or {}
        account_id = data.get('account_id')
        if not account_id:
            accs = fb_api('me/adaccounts', params={'fields': 'id'})
            accts = accs.get('data', [])
            if not accts:
                return jsonify({"recommendations": [], "error": "No ad accounts found"})
            account_id = accts[0]['id']

        # Load config
        with models.db_conn() as db:
            cfg = db.execute("SELECT * FROM scaling_configs WHERE user_id = ? AND (account_id = ? OR account_id = '')",
                             (user['id'], account_id)).fetchone()
        max_increase = cfg['max_budget_increase_pct'] if cfg else 30
        min_roas = cfg['min_roas_threshold'] if cfg else 2.0
        lookback = cfg['lookback_days'] if cfg else 7
        kill_loss = cfg['kill_loss_threshold'] if cfg else 500

        # Get campaign insights
        insights = fb_api(f'{account_id}/insights', params={
            'fields': 'campaign_id,campaign_name,spend,actions,ctr,cpc,cpm,impressions,clicks',
            'date_preset': f'last_{lookback}d',
            'level': 'campaign',
            'limit': 500,
        })

        recommendations = []
        for row in insights.get('data', []):
            spend = safe_float(row.get('spend'))
            ctr = safe_float(row.get('ctr'))
            cpc = safe_float(row.get('cpc'))
            impressions = safe_int(row.get('impressions'))

            # Calculate ROAS from actions
            revenue = 0
            for a in row.get('actions', []):
                if a.get('action_type') in ('purchase', 'offsite_conversion.fb_pixel_purchase'):
                    revenue += safe_float(a.get('value', 0))
            roas = (revenue / spend) if spend > 0 else 0

            rec = {
                "campaign_id": row.get('campaign_id', ''),
                "campaign_name": row.get('campaign_name', ''),
                "spend": spend,
                "roas": round(roas, 2),
                "ctr": round(ctr, 2),
                "cpc": round(cpc, 2),
                "impressions": impressions,
                "revenue": round(revenue, 2),
            }

            if spend > kill_loss and roas < 1.0:
                rec["action"] = "kill"
                rec["reason"] = f"Losing money: spend ฿{spend:.0f} with ROAS {roas:.2f}x"
                rec["severity"] = "critical"
            elif roas >= min_roas and ctr > 1.0:
                increase_pct = min(25, max_increase)
                rec["action"] = "increase_budget"
                rec["increase_pct"] = increase_pct
                rec["reason"] = f"ROAS {roas:.2f}x (>{min_roas}x) with good CTR {ctr:.2f}%"
                rec["severity"] = "positive"
            elif roas < min_roas * 0.7:
                rec["action"] = "decrease_budget"
                rec["decrease_pct"] = 15
                rec["reason"] = f"ROAS {roas:.2f}x below threshold, declining performance"
                rec["severity"] = "warning"
            else:
                rec["action"] = "maintain"
                rec["reason"] = "Performance is within acceptable range"
                rec["severity"] = "neutral"

            recommendations.append(rec)

        return jsonify({
            "recommendations": recommendations,
            "config": {
                "max_budget_increase_pct": max_increase,
                "min_roas_threshold": min_roas,
                "lookback_days": lookback,
                "kill_loss_threshold": kill_loss,
            }
        })
    except Exception as e:
        logger.error(f"analyze_scaling error: {e}")
        return jsonify({"recommendations": [], "error": str(e)}), 500

@app.route('/api/scaling/execute', methods=['POST'])
@require_auth
def execute_scaling(user):
    try:
        data = request.json
        if not data or not data.get('confirm'):
            return jsonify({"error": "Set 'confirm': true to execute scaling changes"}), 400
        actions = data.get('actions', [])
        if not actions:
            return jsonify({"error": "No actions provided"}), 400

        results = []
        for act in actions:
            campaign_id = act.get('campaign_id')
            action = act.get('action')
            if not campaign_id or not action:
                results.append({"campaign_id": campaign_id, "error": "Missing campaign_id or action"})
                continue

            if action == 'increase_budget':
                pct = safe_float(act.get('increase_pct', 20))
                # Get current budget
                camp = fb_api(campaign_id, params={'fields': 'daily_budget'})
                current = safe_float(camp.get('daily_budget'))
                if current > 0:
                    new_budget = int(current * (1 + pct / 100))
                    fb_result = fb_api(campaign_id, method='POST', data={'daily_budget': str(new_budget)})
                    ok = 'error' not in fb_result
                    results.append({"campaign_id": campaign_id, "action": action,
                                    "old_budget": current / 100, "new_budget": new_budget / 100, "ok": ok})
                    if ok:
                        with models.db_conn() as db:
                            db.execute("""INSERT INTO bot_actions (user_id, action_type, target_type, target_id, target_name, details)
                                         VALUES (?, ?, ?, ?, ?, ?)""",
                                       (user['id'], 'scaling_increase', 'campaign', campaign_id, campaign_id,
                                        json.dumps({"pct": pct, "old": current / 100, "new": new_budget / 100})))
                else:
                    results.append({"campaign_id": campaign_id, "error": "Could not read current budget"})

            elif action == 'decrease_budget':
                pct = safe_float(act.get('decrease_pct', 15))
                camp = fb_api(campaign_id, params={'fields': 'daily_budget'})
                current = safe_float(camp.get('daily_budget'))
                if current > 0:
                    new_budget = max(100, int(current * (1 - pct / 100)))  # Min 1.00
                    fb_result = fb_api(campaign_id, method='POST', data={'daily_budget': str(new_budget)})
                    ok = 'error' not in fb_result
                    results.append({"campaign_id": campaign_id, "action": action,
                                    "old_budget": current / 100, "new_budget": new_budget / 100, "ok": ok})
                    if ok:
                        with models.db_conn() as db:
                            db.execute("""INSERT INTO bot_actions (user_id, action_type, target_type, target_id, target_name, details)
                                         VALUES (?, ?, ?, ?, ?, ?)""",
                                       (user['id'], 'scaling_decrease', 'campaign', campaign_id, campaign_id,
                                        json.dumps({"pct": pct, "old": current / 100, "new": new_budget / 100})))

            elif action == 'kill':
                fb_result = fb_api(campaign_id, method='POST', data={'status': 'PAUSED'})
                ok = 'error' not in fb_result
                results.append({"campaign_id": campaign_id, "action": "paused", "ok": ok})
                if ok:
                    with models.db_conn() as db:
                        db.execute("""INSERT INTO bot_actions (user_id, action_type, target_type, target_id, target_name, details)
                                     VALUES (?, ?, ?, ?, ?, ?)""",
                                   (user['id'], 'scaling_kill', 'campaign', campaign_id, campaign_id,
                                    json.dumps({"reason": act.get('reason', 'Scaling kill')})))

            else:
                results.append({"campaign_id": campaign_id, "error": f"Unknown action: {action}"})

        return jsonify({"ok": True, "results": results})
    except Exception as e:
        logger.error(f"execute_scaling error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scaling/kill-switch', methods=['POST'])
@require_auth
def kill_switch(user):
    try:
        data = request.json or {}
        account_id = data.get('account_id')
        threshold = safe_float(data.get('loss_threshold', 500))
        if not account_id:
            accs = fb_api('me/adaccounts', params={'fields': 'id'})
            accts = accs.get('data', [])
            if not accts:
                return jsonify({"error": "No ad accounts found"}), 400
            account_id = accts[0]['id']

        # Find campaigns losing money
        insights = fb_api(f'{account_id}/insights', params={
            'fields': 'campaign_id,campaign_name,spend,actions',
            'date_preset': 'last_7d',
            'level': 'campaign',
        })

        killed = []
        for row in insights.get('data', []):
            spend = safe_float(row.get('spend'))
            revenue = 0
            for a in row.get('actions', []):
                if a.get('action_type') in ('purchase', 'offsite_conversion.fb_pixel_purchase'):
                    revenue += safe_float(a.get('value', 0))
            loss = spend - revenue

            if loss > threshold:
                campaign_id = row.get('campaign_id')
                fb_result = fb_api(campaign_id, method='POST', data={'status': 'PAUSED'})
                if 'error' not in fb_result:
                    killed.append({
                        "campaign_id": campaign_id,
                        "campaign_name": row.get('campaign_name', ''),
                        "spend": spend,
                        "revenue": revenue,
                        "loss": round(loss, 2),
                    })
                    with models.db_conn() as db:
                        db.execute("""INSERT INTO bot_actions (user_id, action_type, target_type, target_id, target_name, details)
                                     VALUES (?, ?, ?, ?, ?, ?)""",
                                   (user['id'], 'kill_switch', 'campaign', campaign_id,
                                    row.get('campaign_name', campaign_id),
                                    json.dumps({"spend": spend, "revenue": revenue, "loss": round(loss, 2)})))

        return jsonify({"ok": True, "killed": killed, "threshold": threshold})
    except Exception as e:
        logger.error(f"kill_switch error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Feature 2: Creative Fatigue Detection ───

@app.route('/api/fb/fatigue', methods=['GET'])
@require_auth
def fatigue_all(user):
    try:
        account_id = request.args.get('account_id')
        if not account_id:
            accs = fb_api('me/adaccounts', params={'fields': 'id'})
            accts = accs.get('data', [])
            if not accts:
                return jsonify({"fatigued_ads": []})
            account_id = accts[0]['id']

        # Get last 7 days daily insights at ad level
        result = fb_api(f'{account_id}/insights', params={
            'fields': 'ad_id,ad_name,ctr,impressions,clicks,spend',
            'date_preset': 'last_7d',
            'time_increment': 1,
            'level': 'ad',
            'limit': 500,
        })

        if 'error' in result and 'data' not in result:
            return jsonify({"fatigued_ads": [], "error": result['error']})

        # Group by ad_id
        ad_data = {}
        for row in result.get('data', []):
            ad_id = row.get('ad_id', '')
            if ad_id not in ad_data:
                ad_data[ad_id] = {"name": row.get('ad_name', ''), "rows": []}
            ad_data[ad_id]["rows"].append({
                "date": row.get('date_start', ''),
                "ctr": safe_float(row.get('ctr')),
                "impressions": safe_int(row.get('impressions')),
            })

        fatigued = []
        for ad_id, info in ad_data.items():
            rows = sorted(info['rows'], key=lambda x: x['date'])
            if len(rows) < 4:
                continue

            recent_3 = rows[-3:]
            earlier = rows[:-3]

            avg_recent = sum(r['ctr'] for r in recent_3) / len(recent_3) if recent_3 else 0
            avg_earlier = sum(r['ctr'] for r in earlier) / len(earlier) if earlier else 0

            if avg_earlier > 0:
                drop_pct = ((avg_earlier - avg_recent) / avg_earlier) * 100
            else:
                drop_pct = 0

            if drop_pct > 30:
                severity = "critical" if drop_pct > 50 else "warning"
                fatigued.append({
                    "ad_id": ad_id,
                    "ad_name": info['name'],
                    "ctr_recent_3d": round(avg_recent, 2),
                    "ctr_prev_7d": round(avg_earlier, 2),
                    "drop_pct": round(drop_pct, 1),
                    "severity": severity,
                    "recommendation": "Refresh creative immediately" if severity == "critical"
                                     else "Consider testing new creative",
                })

        return jsonify({"fatigued_ads": fatigued, "total_ads_analyzed": len(ad_data)})
    except Exception as e:
        logger.error(f"fatigue_all error: {e}")
        return jsonify({"fatigued_ads": [], "error": str(e)}), 500

@app.route('/api/fb/fatigue/<ad_id>', methods=['GET'])
@require_auth
def fatigue_single(user, ad_id):
    try:
        result = fb_api(f'{ad_id}/insights', params={
            'fields': 'ad_id,ad_name,ctr,impressions,clicks,spend,date_start',
            'date_preset': 'last_14d',
            'time_increment': 1,
            'level': 'ad',
        })

        if 'error' in result and 'data' not in result:
            return jsonify({"error": result['error']}), 400

        rows = sorted(result.get('data', []), key=lambda x: x.get('date_start', ''))
        if len(rows) < 4:
            return jsonify({"ad_id": ad_id, "fatigue": None, "message": "Not enough data (need 4+ days)"})

        recent_3 = rows[-3:]
        earlier = rows[:-3]
        avg_recent = sum(safe_float(r.get('ctr')) for r in recent_3) / len(recent_3)
        avg_earlier = sum(safe_float(r.get('ctr')) for r in earlier) / len(earlier) if earlier else 0

        drop_pct = ((avg_earlier - avg_recent) / avg_earlier * 100) if avg_earlier > 0 else 0
        severity = "critical" if drop_pct > 50 else ("warning" if drop_pct > 30 else "healthy")

        return jsonify({
            "ad_id": ad_id,
            "fatigue": {
                "severity": severity,
                "ctr_recent_3d": round(avg_recent, 2),
                "ctr_prev_period": round(avg_earlier, 2),
                "drop_pct": round(drop_pct, 1),
                "daily_data": [{"date": r.get('date_start'), "ctr": safe_float(r.get('ctr')),
                               "impressions": safe_int(r.get('impressions'))} for r in rows],
                "recommendation": "Refresh creative immediately" if severity == "critical"
                                 else ("Consider new creative" if severity == "warning"
                                       else "Creative performing well"),
            }
        })
    except Exception as e:
        logger.error(f"fatigue_single error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Feature 3: Budget Pacing Dashboard ───

@app.route('/api/fb/pacing', methods=['GET'])
@require_auth
def budget_pacing(user):
    try:
        account_id = request.args.get('account_id')
        if not account_id:
            accs = fb_api('me/adaccounts', params={'fields': 'id'})
            accts = accs.get('data', [])
            if not accts:
                return jsonify({"pacing": []})
            account_id = accts[0]['id']

        # Get campaigns with budgets
        campaigns = fb_api(f'{account_id}/campaigns', params={
            'fields': 'id,name,daily_budget,status',
            'limit': 500,
        })

        # Get today's spend per campaign
        today_insights = fb_api(f'{account_id}/insights', params={
            'fields': 'campaign_id,spend',
            'date_preset': 'today',
            'level': 'campaign',
            'limit': 500,
        })

        today_spend = {}
        for row in today_insights.get('data', []):
            today_spend[row.get('campaign_id', '')] = safe_float(row.get('spend'))

        now = datetime.utcnow()
        hours_passed = now.hour + now.minute / 60
        hours_remaining = max(0, 24 - hours_passed)

        pacing = []
        for c in campaigns.get('data', []):
            daily_budget_raw = c.get('daily_budget')
            if not daily_budget_raw:
                continue
            daily_budget = safe_float(daily_budget_raw) / 100
            if daily_budget <= 0:
                continue

            spent = today_spend.get(c['id'], 0)
            progress_pct = (spent / daily_budget * 100) if daily_budget > 0 else 0
            burn_rate = spent / hours_passed if hours_passed > 0 else 0
            forecast_hours = (daily_budget - spent) / burn_rate if burn_rate > 0 else 999
            forecast_exhaust = (now + timedelta(hours=forecast_hours)).strftime('%H:%M') if forecast_hours < 24 else 'N/A'

            if progress_pct > 120 and hours_passed < 20:
                status = "overspending"
            elif progress_pct < 50 and hours_passed > 14:
                status = "underspending"
            else:
                status = "onschedule"

            pacing.append({
                "campaign_id": c['id'],
                "campaign_name": c.get('name', ''),
                "daily_budget": daily_budget,
                "spent_today": round(spent, 2),
                "progress_pct": round(progress_pct, 1),
                "burn_rate_per_hour": round(burn_rate, 2),
                "forecast_exhaust_time": forecast_exhaust,
                "pacing_status": status,
                "hours_passed": round(hours_passed, 1),
                "hours_remaining": round(hours_remaining, 1),
            })

        return jsonify({"pacing": pacing})
    except Exception as e:
        logger.error(f"budget_pacing error: {e}")
        return jsonify({"pacing": [], "error": str(e)}), 500

# ─── Feature 4: Multi-Account Management ───

@app.route('/api/fb/accounts/compare', methods=['GET'])
@require_auth
def accounts_compare(user):
    try:
        result = fb_api('me/adaccounts', params={
            'fields': 'id,name,account_status,currency,timezone_name',
            'limit': 500,
        })
        if 'error' in result and 'data' not in result:
            return jsonify({"accounts": [], "error": result['error']})

        comparisons = []
        for acc in result.get('data', [])[:20]:  # Limit to 20 accounts
            acc_id = acc['id']
            insights = fb_api(f'{acc_id}/insights', params={
                'fields': 'impressions,clicks,spend,reach,ctr,cpc,cpm,actions',
                'date_preset': 'last_7d',
                'level': 'account',
            })
            data = insights.get('data', [])
            if data:
                row = data[0]
                revenue = 0
                for a in row.get('actions', []):
                    if a.get('action_type') in ('purchase', 'offsite_conversion.fb_pixel_purchase'):
                        revenue += safe_float(a.get('value', 0))
                spend = safe_float(row.get('spend'))
                comparisons.append({
                    "account_id": acc_id,
                    "account_name": acc.get('name', ''),
                    "currency": acc.get('currency', 'USD'),
                    "impressions": safe_int(row.get('impressions')),
                    "clicks": safe_int(row.get('clicks')),
                    "spend": spend,
                    "reach": safe_int(row.get('reach')),
                    "ctr": safe_float(row.get('ctr')),
                    "cpc": safe_float(row.get('cpc')),
                    "cpm": safe_float(row.get('cpm')),
                    "revenue": round(revenue, 2),
                    "roas": round(revenue / spend, 2) if spend > 0 else 0,
                })
            else:
                comparisons.append({
                    "account_id": acc_id,
                    "account_name": acc.get('name', ''),
                    "currency": acc.get('currency', 'USD'),
                    "impressions": 0, "clicks": 0, "spend": 0, "reach": 0,
                    "ctr": 0, "cpc": 0, "cpm": 0, "revenue": 0, "roas": 0,
                })

        return jsonify({"accounts": comparisons})
    except Exception as e:
        logger.error(f"accounts_compare error: {e}")
        return jsonify({"accounts": [], "error": str(e)}), 500

@app.route('/api/fb/accounts/<account_id>/summary', methods=['GET'])
@require_auth
def account_summary(user, account_id):
    try:
        if not account_id:
            return jsonify({"error": "Account ID required"}), 400

        acc_info = fb_api(account_id, params={
            'fields': 'id,name,account_status,currency,timezone_name,business_name'
        })
        if 'error' in acc_info:
            return jsonify({"error": acc_info['error']}), 400

        insights = fb_api(f'{account_id}/insights', params={
            'fields': 'impressions,clicks,spend,reach,ctr,cpc,cpm,actions',
            'date_preset': 'last_7d',
            'level': 'account',
        })

        data = insights.get('data', [])
        summary = {}
        if data:
            row = data[0]
            actions = {}
            revenue = 0
            for a in row.get('actions', []):
                actions[a.get('action_type', '')] = a.get('value', 0)
                if a.get('action_type') in ('purchase', 'offsite_conversion.fb_pixel_purchase'):
                    revenue += safe_float(a.get('value', 0))
            spend = safe_float(row.get('spend'))
            summary = {
                "impressions": safe_int(row.get('impressions')),
                "clicks": safe_int(row.get('clicks')),
                "spend": spend,
                "reach": safe_int(row.get('reach')),
                "ctr": safe_float(row.get('ctr')),
                "cpc": safe_float(row.get('cpc')),
                "cpm": safe_float(row.get('cpm')),
                "actions": actions,
                "revenue": round(revenue, 2),
                "roas": round(revenue / spend, 2) if spend > 0 else 0,
            }

        return jsonify({
            "account": {
                "id": acc_info.get('id', account_id),
                "name": acc_info.get('name', ''),
                "status": acc_info.get('account_status', ''),
                "currency": acc_info.get('currency', 'USD'),
                "timezone": acc_info.get('timezone_name', ''),
                "business": acc_info.get('business_name', ''),
            },
            "summary": summary,
        })
    except Exception as e:
        logger.error(f"account_summary error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Feature 5: A/B Test Tracker ───

@app.route('/api/experiments', methods=['POST'])
@require_auth
def create_experiment(user):
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Experiment data required"}), 400
        name = data.get('name')
        variant_a = data.get('variant_a_adset_id')
        variant_b = data.get('variant_b_adset_id')
        if not name or not variant_a or not variant_b:
            return jsonify({"error": "name, variant_a_adset_id, variant_b_adset_id are required"}), 400
        metric = data.get('metric', 'cpc')
        valid_metrics = ('cpc', 'ctr', 'cpm', 'roas', 'cpa', 'conversion_rate')
        if metric not in valid_metrics:
            return jsonify({"error": f"metric must be one of: {', '.join(valid_metrics)}"}), 400
        duration = safe_int(data.get('duration_days'), 7)
        if duration < 1 or duration > 90:
            return jsonify({"error": "duration_days must be 1-90"}), 400

        with models.db_conn() as db:
            cursor = db.execute(
                """INSERT INTO experiments (user_id, name, account_id, variant_a_adset_id, variant_b_adset_id, metric, duration_days)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user['id'], name, data.get('account_id', ''), variant_a, variant_b, metric, duration)
            )
            exp_id = cursor.lastrowid
        return jsonify({"ok": True, "id": exp_id})
    except Exception as e:
        logger.error(f"create_experiment error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/experiments', methods=['GET'])
@require_auth
def list_experiments(user):
    try:
        with models.db_conn() as db:
            rows = db.execute("SELECT * FROM experiments WHERE user_id = ? ORDER BY created_at DESC",
                              (user['id'],)).fetchall()
        experiments = []
        for r in rows:
            experiments.append({
                "id": r['id'],
                "name": r['name'],
                "account_id": r['account_id'],
                "variant_a_adset_id": r['variant_a_adset_id'],
                "variant_b_adset_id": r['variant_b_adset_id'],
                "metric": r['metric'],
                "duration_days": r['duration_days'],
                "status": r['status'],
                "winner": r['winner'],
                "created_at": r['created_at'],
            })
        return jsonify({"experiments": experiments})
    except Exception as e:
        logger.error(f"list_experiments error: {e}")
        return jsonify({"experiments": [], "error": str(e)}), 500

@app.route('/api/experiments/<int:exp_id>', methods=['GET'])
@require_auth
def get_experiment(user, exp_id):
    try:
        with models.db_conn() as db:
            r = db.execute("SELECT * FROM experiments WHERE id = ? AND user_id = ?",
                           (exp_id, user['id'])).fetchone()
        if not r:
            return jsonify({"error": "Experiment not found"}), 404

        exp = dict(r)
        # Fetch live data for both variants
        variant_a_data = _get_adset_metrics(exp['variant_a_adset_id'], exp['metric'])
        variant_b_data = _get_adset_metrics(exp['variant_b_adset_id'], exp['metric'])

        return jsonify({"experiment": {
            "id": exp['id'],
            "name": exp['name'],
            "account_id": exp['account_id'],
            "variant_a_adset_id": exp['variant_a_adset_id'],
            "variant_b_adset_id": exp['variant_b_adset_id'],
            "metric": exp['metric'],
            "duration_days": exp['duration_days'],
            "status": exp['status'],
            "winner": exp['winner'],
            "conclusion": exp['conclusion'],
            "variant_a": variant_a_data,
            "variant_b": variant_b_data,
            "created_at": exp['created_at'],
        }})
    except Exception as e:
        logger.error(f"get_experiment error: {e}")
        return jsonify({"error": str(e)}), 500

def _get_adset_metrics(adset_id, metric):
    """Fetch metrics for a single ad set."""
    try:
        result = fb_api(f'{adset_id}/insights', params={
            'fields': 'impressions,clicks,spend,actions,ctr,cpc,cpm',
            'date_preset': 'last_7d',
        })
        data = result.get('data', [])
        if not data:
            return {"adset_id": adset_id, "impressions": 0, "clicks": 0, "spend": 0,
                    "ctr": 0, "cpc": 0, "cpm": 0, "metric_value": 0}
        row = data[0]
        spend = safe_float(row.get('spend'))
        ctr = safe_float(row.get('ctr'))
        cpc = safe_float(row.get('cpc'))
        cpm = safe_float(row.get('cpm'))

        revenue = 0
        conversions = 0
        for a in row.get('actions', []):
            if a.get('action_type') in ('purchase', 'offsite_conversion.fb_pixel_purchase'):
                revenue += safe_float(a.get('value', 0))
                conversions += 1

        roas = revenue / spend if spend > 0 else 0
        cpa = spend / conversions if conversions > 0 else 0
        conversion_rate = (conversions / safe_int(row.get('clicks')) * 100) if safe_int(row.get('clicks')) > 0 else 0

        metric_map = {
            'cpc': cpc, 'ctr': ctr, 'cpm': cpm,
            'roas': roas, 'cpa': cpa, 'conversion_rate': conversion_rate,
        }

        return {
            "adset_id": adset_id,
            "impressions": safe_int(row.get('impressions')),
            "clicks": safe_int(row.get('clicks')),
            "spend": spend,
            "ctr": round(ctr, 2),
            "cpc": round(cpc, 2),
            "cpm": round(cpm, 2),
            "roas": round(roas, 2),
            "cpa": round(cpa, 2),
            "conversions": conversions,
            "metric_value": round(metric_map.get(metric, cpc), 2),
        }
    except Exception as e:
        logger.error(f"_get_adset_metrics error for {adset_id}: {e}")
        return {"adset_id": adset_id, "error": str(e), "metric_value": 0}

@app.route('/api/experiments/<int:exp_id>/conclude', methods=['POST'])
@require_auth
def conclude_experiment(user, exp_id):
    try:
        with models.db_conn() as db:
            r = db.execute("SELECT * FROM experiments WHERE id = ? AND user_id = ?",
                           (exp_id, user['id'])).fetchone()
        if not r:
            return jsonify({"error": "Experiment not found"}), 404
        if r['status'] != 'running':
            return jsonify({"error": "Experiment is not running"}), 400

        exp = dict(r)
        a_data = _get_adset_metrics(exp['variant_a_adset_id'], exp['metric'])
        b_data = _get_adset_metrics(exp['variant_b_adset_id'], exp['metric'])

        a_val = a_data.get('metric_value', 0)
        b_val = b_data.get('metric_value', 0)

        # Determine winner based on metric direction
        lower_is_better = exp['metric'] in ('cpc', 'cpm', 'cpa')
        if a_val == 0 and b_val == 0:
            winner = None
            conclusion = "Insufficient data to determine winner"
        elif lower_is_better:
            winner = 'A' if a_val < b_val else ('B' if b_val < a_val else None)
            if winner:
                pct_diff = abs(a_val - b_val) / max(a_val, b_val) * 100 if max(a_val, b_val) > 0 else 0
                conclusion = f"Variant {winner} wins with {exp['metric']}={min(a_val, b_val):.2f} vs {max(a_val, b_val):.2f} ({pct_diff:.1f}% better)"
            else:
                conclusion = "Both variants have identical performance"
        else:
            winner = 'A' if a_val > b_val else ('B' if b_val > a_val else None)
            if winner:
                pct_diff = abs(a_val - b_val) / max(a_val, b_val) * 100 if max(a_val, b_val) > 0 else 0
                conclusion = f"Variant {winner} wins with {exp['metric']}={max(a_val, b_val):.2f} vs {min(a_val, b_val):.2f} ({pct_diff:.1f}% better)"
            else:
                conclusion = "Both variants have identical performance"

        with models.db_conn() as db:
            db.execute("UPDATE experiments SET status='concluded', winner=?, conclusion=?, updated_at=datetime('now') WHERE id=?",
                       (winner, conclusion, exp_id))

        return jsonify({"ok": True, "winner": winner, "conclusion": conclusion,
                        "variant_a": a_data, "variant_b": b_data})
    except Exception as e:
        logger.error(f"conclude_experiment error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/experiments/<int:exp_id>', methods=['DELETE'])
@require_auth
def delete_experiment(user, exp_id):
    try:
        with models.db_conn() as db:
            result = db.execute("DELETE FROM experiments WHERE id = ? AND user_id = ?",
                                (exp_id, user['id']))
            if result.rowcount == 0:
                return jsonify({"error": "Experiment not found"}), 404
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"delete_experiment error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Feature 6: Budget Calendar ───

@app.route('/api/fb/budget-calendar', methods=['GET'])
@require_auth
def budget_calendar(user):
    try:
        limit = request.args.get('limit', 50, type=int)
        limit = min(max(limit, 1), 200)

        with models.db_conn() as db:
            rows = db.execute(
                """SELECT * FROM bot_actions
                   WHERE user_id = ? AND action_type = 'budget_change'
                   ORDER BY created_at DESC LIMIT ?""",
                (user['id'], limit)
            ).fetchall()

        calendar = []
        for r in rows:
            details = json.loads(r['details']) if r['details'] else {}
            target_id = r['target_id']

            # Try to get insights for that day
            insights_data = {}
            if target_id:
                try:
                    ins = fb_api(f'{target_id}/insights', params={
                        'fields': 'spend,ctr,cpc,cpm,impressions,actions',
                        'date_preset': 'last_7d',
                    })
                    if ins.get('data'):
                        row_ins = ins['data'][0]
                        revenue = 0
                        for a in row_ins.get('actions', []):
                            if a.get('action_type') in ('purchase', 'offsite_conversion.fb_pixel_purchase'):
                                revenue += safe_float(a.get('value', 0))
                        spend = safe_float(row_ins.get('spend'))
                        insights_data = {
                            "spend": spend,
                            "ctr": safe_float(row_ins.get('ctr')),
                            "cpc": safe_float(row_ins.get('cpc')),
                            "cpm": safe_float(row_ins.get('cpm')),
                            "impressions": safe_int(row_ins.get('impressions')),
                            "revenue": round(revenue, 2),
                            "roas": round(revenue / spend, 2) if spend > 0 else 0,
                        }
                except Exception:
                    pass

            calendar.append({
                "id": r['id'],
                "campaign_id": target_id,
                "campaign_name": r['target_name'],
                "new_budget": details.get('budget'),
                "budget_type": details.get('type', 'daily'),
                "created_at": r['created_at'],
                "outcome": insights_data,
            })

        return jsonify({"calendar": calendar})
    except Exception as e:
        logger.error(f"budget_calendar error: {e}")
        return jsonify({"calendar": [], "error": str(e)}), 500

# ─── Feature 7: Notifications (Slack/Discord/Telegram) ───

@app.route('/api/notifications/webhook/connect', methods=['POST'])
@require_auth
def connect_webhook(user):
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Webhook data required"}), 400
        webhook_url = data.get('webhook_url', '').strip()
        webhook_type = data.get('webhook_type', '').strip()
        name = data.get('name', '').strip()

        if not webhook_url:
            return jsonify({"error": "webhook_url required"}), 400
        if webhook_type not in ('slack', 'discord'):
            return jsonify({"error": "webhook_type must be 'slack' or 'discord'"}), 400

        # Validate URL format
        if not webhook_url.startswith('https://'):
            return jsonify({"error": "webhook_url must start with https://"}), 400

        with models.db_conn() as db:
            db.execute(
                "INSERT INTO notification_channels (user_id, channel_type, webhook_url, name) VALUES (?, ?, ?, ?)",
                (user['id'], webhook_type, webhook_url, name or f"{webhook_type.capitalize()} Webhook")
            )
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"connect_webhook error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/notifications/webhook/test-send', methods=['POST'])
@require_auth
def test_webhook(user):
    try:
        data = request.json
        if not data or not data.get('channel_id'):
            return jsonify({"error": "channel_id required"}), 400

        with models.db_conn() as db:
            channel = db.execute("SELECT * FROM notification_channels WHERE id = ? AND user_id = ?",
                                 (data['channel_id'], user['id'])).fetchone()
        if not channel:
            return jsonify({"error": "Channel not found"}), 404

        import requests as req
        ch_type = channel['channel_type']
        url = channel['webhook_url']

        if ch_type == 'slack':
            payload = {
                "blocks": [
                    {"type": "header", "text": {"type": "plain_text", "text": "🧪 Acex Ads Test"}},
                    {"type": "section", "text": {"type": "mrkdwn",
                        "text": "Test message from *Acex Ads*.\nNotifications are working! ✅"}},
                ]
            }
        elif ch_type == 'discord':
            payload = {
                "embeds": [{
                    "title": "🧪 Acex Ads Test",
                    "description": "Test message from **Acex Ads**.\nNotifications are working! ✅",
                    "color": 5814783,
                }]
            }
        else:
            return jsonify({"error": f"Unsupported channel type: {ch_type}"}), 400

        resp = req.post(url, json=payload, timeout=10)
        if resp.status_code in (200, 204):
            return jsonify({"ok": True, "message": f"Test message sent to {ch_type}!"})
        return jsonify({"error": f"{ch_type} API returned {resp.status_code}: {resp.text}"}), 400
    except Exception as e:
        logger.error(f"test_webhook error: {e}")
        return jsonify({"error": str(e)}), 500

def send_notification(user_id: int, message: str, title: str = "Acex Ads Alert"):
    """Send notification to all connected channels for a user."""
    import requests as req

    # Telegram
    try:
        with models.db_conn() as db:
            tg = db.execute(
                "SELECT * FROM telegram_connections WHERE user_id = ? AND connected = 1",
                (user_id,)
            ).fetchall()
        for conn in tg:
            try:
                req.post(
                    f"https://api.telegram.org/bot{conn['bot_token']}/sendMessage",
                    json={"chat_id": conn['chat_id'], "text": f"📢 {title}\n\n{message}", "parse_mode": "Markdown"},
                    timeout=10
                )
            except Exception as e:
                logger.error(f"Telegram send error: {e}")
    except Exception:
        pass

    # Slack / Discord
    try:
        with models.db_conn() as db:
            channels = db.execute(
                "SELECT * FROM notification_channels WHERE user_id = ? AND connected = 1",
                (user_id,)
            ).fetchall()
        for ch in channels:
            try:
                if ch['channel_type'] == 'slack':
                    payload = {
                        "blocks": [
                            {"type": "header", "text": {"type": "plain_text", "text": title}},
                            {"type": "section", "text": {"type": "mrkdwn", "text": message}},
                        ]
                    }
                elif ch['channel_type'] == 'discord':
                    payload = {
                        "embeds": [{
                            "title": title,
                            "description": message,
                            "color": 16750848,
                        }]
                    }
                else:
                    continue
                req.post(ch['webhook_url'], json=payload, timeout=10)
            except Exception as e:
                logger.error(f"Webhook send error ({ch['channel_type']}): {e}")
    except Exception:
        pass

# ─── Feature 8: AdsGPT with OpenAI ───

@app.route('/api/ads-gpt/settings', methods=['POST'])
@require_auth
def save_ads_gpt_settings(user):
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Settings data required"}), 400
        openai_key = data.get('openai_api_key', '').strip()
        with models.db_conn() as db:
            existing = db.execute("SELECT value FROM settings WHERE user_id = ? AND key = ?",
                                  (user['id'], 'openai_api_key')).fetchone()
            if existing:
                db.execute("UPDATE settings SET value = ? WHERE user_id = ? AND key = ?",
                           (openai_key, user['id'], 'openai_api_key'))
            else:
                db.execute("INSERT INTO settings (user_id, key, value) VALUES (?, ?, ?)",
                           (user['id'], 'openai_api_key', openai_key))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"save_ads_gpt_settings error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ads-gpt/conversations', methods=['GET'])
@require_auth
def get_conversations(user):
    try:
        with models.db_conn() as db:
            rows = db.execute(
                "SELECT id, title, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
                (user['id'],)
            ).fetchall()
        convos = [{"id": r['id'], "title": r['title'], "created_at": r['created_at'],
                   "updated_at": r['updated_at']} for r in rows]
        return jsonify({"conversations": convos})
    except Exception as e:
        logger.error(f"get_conversations error: {e}")
        return jsonify({"conversations": [], "error": str(e)}), 500

@app.route('/api/ads-gpt/conversations/<int:conv_id>', methods=['GET'])
@require_auth
def get_conversation(user, conv_id):
    try:
        with models.db_conn() as db:
            r = db.execute("SELECT * FROM conversations WHERE id = ? AND user_id = ?",
                           (conv_id, user['id'])).fetchone()
        if not r:
            return jsonify({"error": "Conversation not found"}), 404
        return jsonify({"conversation": {
            "id": r['id'],
            "title": r['title'],
            "messages": json.loads(r['messages']) if r['messages'] else [],
            "created_at": r['created_at'],
            "updated_at": r['updated_at'],
        }})
    except Exception as e:
        logger.error(f"get_conversation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ads-gpt/conversations/<int:conv_id>', methods=['DELETE'])
@require_auth
def delete_conversation(user, conv_id):
    try:
        with models.db_conn() as db:
            result = db.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?",
                                (conv_id, user['id']))
            if result.rowcount == 0:
                return jsonify({"error": "Conversation not found"}), 404
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"delete_conversation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ads-gpt/chat', methods=['POST'])
@require_auth
def ads_gpt_chat(user):
    try:
        data = request.json
        if not data or not data.get('message'):
            return jsonify({"error": "Message required"}), 400

        message = data['message'].strip()
        if not message:
            return jsonify({"error": "Message cannot be empty"}), 400
        conversation_id = data.get('conversation_id')
        streaming = data.get('streaming', False)

        # Load or create conversation
        with models.db_conn() as db:
            if conversation_id:
                conv = db.execute("SELECT * FROM conversations WHERE id = ? AND user_id = ?",
                                 (conversation_id, user['id'])).fetchone()
                if conv:
                    messages = json.loads(conv['messages']) if conv['messages'] else []
                else:
                    messages = []
                    conversation_id = None
            else:
                messages = []

        # Build FB context
        fb_data = {}
        try:
            campaigns = fb_api('me/adaccounts', params={'fields': 'id'})
            if campaigns.get('data'):
                acc_id = campaigns['data'][0]['id']
                camp_result = fb_api(f'{acc_id}/campaigns', params={
                    'fields': 'id,name,status,daily_budget', 'limit': 10})
                fb_data['campaigns'] = camp_result.get('data', [])
                ins_result = fb_api(f'{acc_id}/insights', params={
                    'fields': 'spend,ctr,cpc,cpm,impressions,actions',
                    'date_preset': 'last_7d', 'level': 'campaign', 'limit': 10})
                fb_data['insights'] = ins_result.get('data', [])
        except Exception:
            pass

        # Add user message
        messages.append({"role": "user", "content": message, "timestamp": datetime.now().isoformat()})

        # Use user's OpenAI key if available
        import config as cfg
        original_key = cfg.OPENAI_API_KEY
        try:
            with models.db_conn() as db:
                key_row = db.execute("SELECT value FROM settings WHERE user_id = ? AND key = 'openai_api_key'",
                                     (user['id'],)).fetchone()
            if key_row and key_row['value']:
                cfg.OPENAI_API_KEY = key_row['value']

            if streaming:
                def generate():
                    full_response = ""
                    for chunk in ai_service.generate_response_stream(message, messages[:-1], fb_data):
                        parsed = json.loads(chunk.replace('data: ', '').strip())
                        full_response += parsed.get('content', '')
                        yield chunk
                    # Save after streaming completes
                    messages.append({"role": "assistant", "content": full_response,
                                    "timestamp": datetime.now().isoformat()})
                    title = message[:50] + ('...' if len(message) > 50 else '')
                    with models.db_conn() as db:
                        if conversation_id:
                            db.execute("UPDATE conversations SET messages=?, updated_at=datetime('now') WHERE id=?",
                                       (json.dumps(messages), conversation_id))
                        else:
                            db.execute("INSERT INTO conversations (user_id, title, messages) VALUES (?, ?, ?)",
                                       (user['id'], title, json.dumps(messages)))

                return Response(generate(), mimetype='text/event-stream',
                              headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

            ai_response = ai_service.generate_response(message, messages[:-1], fb_data)
        finally:
            cfg.OPENAI_API_KEY = original_key

        messages.append({"role": "assistant", "content": ai_response, "timestamp": datetime.now().isoformat()})

        title = message[:50] + ('...' if len(message) > 50 else '')
        with models.db_conn() as db:
            if conversation_id:
                db.execute("UPDATE conversations SET messages = ?, updated_at = datetime('now') WHERE id = ?",
                           (json.dumps(messages), conversation_id))
            else:
                cursor = db.execute(
                    "INSERT INTO conversations (user_id, title, messages) VALUES (?, ?, ?)",
                    (user['id'], title, json.dumps(messages))
                )
                conversation_id = cursor.lastrowid

        return jsonify({
            "response": ai_response,
            "conversation_id": conversation_id,
            "messages": messages,
        })
    except Exception as e:
        logger.error(f"ads_gpt_chat error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Feature 9: Anomaly Detection ───

@app.route('/api/fb/anomalies', methods=['GET'])
@require_auth
def detect_anomalies(user):
    try:
        account_id = request.args.get('account_id')
        if not account_id:
            accs = fb_api('me/adaccounts', params={'fields': 'id'})
            accts = accs.get('data', [])
            if not accts:
                return jsonify({"anomalies": []})
            account_id = accts[0]['id']

        # Get last 7 days daily data at campaign level
        result = fb_api(f'{account_id}/insights', params={
            'fields': 'campaign_id,campaign_name,cpc,cpm,ctr,spend,impressions,clicks',
            'date_preset': 'last_7d',
            'time_increment': 1,
            'level': 'campaign',
            'limit': 500,
        })

        if 'error' in result and 'data' not in result:
            return jsonify({"anomalies": [], "error": result['error']})

        # Group by campaign
        campaign_data = {}
        for row in result.get('data', []):
            cid = row.get('campaign_id', '')
            if cid not in campaign_data:
                campaign_data[cid] = {"name": row.get('campaign_name', ''), "rows": []}
            campaign_data[cid]["rows"].append({
                "date": row.get('date_start', ''),
                "cpc": safe_float(row.get('cpc')),
                "cpm": safe_float(row.get('cpm')),
                "ctr": safe_float(row.get('ctr')),
                "spend": safe_float(row.get('spend')),
            })

        anomalies = []
        metrics_to_check = ['cpc', 'cpm', 'ctr', 'spend']

        for cid, info in campaign_data.items():
            rows = sorted(info['rows'], key=lambda x: x['date'])
            if len(rows) < 3:
                continue

            today = rows[-1]
            historical = rows[:-1]

            for metric in metrics_to_check:
                values = [r[metric] for r in historical if r[metric] > 0]
                if len(values) < 2:
                    continue

                mean = sum(values) / len(values)
                variance = sum((x - mean) ** 2 for x in values) / len(values)
                std = sqrt(variance) if variance > 0 else 0

                today_val = today[metric]
                if std > 0:
                    z_score = (today_val - mean) / std
                else:
                    z_score = 0 if today_val == mean else 999

                if abs(z_score) > 2:
                    anomalies.append({
                        "campaign_id": cid,
                        "campaign_name": info['name'],
                        "metric": metric,
                        "actual_value": round(today_val, 2),
                        "expected_range": f"{round(mean - 2*std, 2)} - {round(mean + 2*std, 2)}",
                        "mean": round(mean, 2),
                        "std_dev": round(std, 2),
                        "z_score": round(z_score, 2),
                        "severity": "critical" if abs(z_score) > 3 else "warning",
                        "direction": "spike" if z_score > 0 else "drop",
                        "date": today['date'],
                    })

        anomalies.sort(key=lambda x: abs(x['z_score']), reverse=True)
        return jsonify({"anomalies": anomalies, "campaigns_analyzed": len(campaign_data)})
    except Exception as e:
        logger.error(f"detect_anomalies error: {e}")
        return jsonify({"anomalies": [], "error": str(e)}), 500

# ─── Rules API ───

@app.route('/api/rules', methods=['GET'])
@require_auth
def get_rules(user):
    try:
        with models.db_conn() as db:
            rows = db.execute("SELECT * FROM rules WHERE user_id = ? ORDER BY created_at DESC",
                              (user['id'],)).fetchall()
        rules = []
        for r in rows:
            rules.append({
                "id": r['id'],
                "name": r['name'],
                "description": r['description'],
                "account_id": r['account_id'],
                "conditions": json.loads(r['conditions']) if r['conditions'] else [],
                "actions": json.loads(r['actions']) if r['actions'] else [],
                "status": r['status'],
                "schedule": json.loads(r['schedule']) if r['schedule'] else {},
                "last_run": r['last_run'],
                "run_count": r['run_count'],
                "created_at": r['created_at'],
                "updated_at": r['updated_at'],
            })
        return jsonify({"rules": rules})
    except Exception as e:
        logger.error(f"get_rules error: {e}")
        return jsonify({"rules": [], "error": str(e)}), 500

@app.route('/api/rules', methods=['POST'])
@require_auth
def create_rule(user):
    try:
        data = request.json
        if not data or not data.get('name'):
            return jsonify({"error": "Rule name required"}), 400
        with models.db_conn() as db:
            cursor = db.execute(
                """INSERT INTO rules (user_id, name, description, account_id, conditions, actions, status, schedule)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user['id'], data['name'], data.get('description', ''),
                 data.get('account_id', ''),
                 json.dumps(data.get('conditions', [])),
                 json.dumps(data.get('actions', [])),
                 data.get('status', 'active'),
                 json.dumps(data.get('schedule', {})))
            )
            rule_id = cursor.lastrowid
        return jsonify({"ok": True, "id": rule_id})
    except Exception as e:
        logger.error(f"create_rule error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/rules/<int:rule_id>', methods=['GET'])
@require_auth
def get_rule(user, rule_id):
    try:
        with models.db_conn() as db:
            r = db.execute("SELECT * FROM rules WHERE id = ? AND user_id = ?",
                           (rule_id, user['id'])).fetchone()
        if not r:
            return jsonify({"error": "Rule not found"}), 404
        return jsonify({"rule": {
            "id": r['id'],
            "name": r['name'],
            "description": r['description'],
            "account_id": r['account_id'],
            "conditions": json.loads(r['conditions']) if r['conditions'] else [],
            "actions": json.loads(r['actions']) if r['actions'] else [],
            "status": r['status'],
            "schedule": json.loads(r['schedule']) if r['schedule'] else {},
            "last_run": r['last_run'],
            "run_count": r['run_count'],
            "created_at": r['created_at'],
            "updated_at": r['updated_at'],
        }})
    except Exception as e:
        logger.error(f"get_rule error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/rules/<int:rule_id>', methods=['PUT'])
@require_auth
def update_rule(user, rule_id):
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Rule data required"}), 400
        with models.db_conn() as db:
            db.execute(
                """UPDATE rules SET name=?, description=?, account_id=?, conditions=?, actions=?,
                   status=?, schedule=?, updated_at=datetime('now')
                   WHERE id=? AND user_id=?""",
                (data.get('name', ''), data.get('description', ''),
                 data.get('account_id', ''),
                 json.dumps(data.get('conditions', [])),
                 json.dumps(data.get('actions', [])),
                 data.get('status', 'active'),
                 json.dumps(data.get('schedule', {})),
                 rule_id, user['id'])
            )
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"update_rule error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/rules/<int:rule_id>', methods=['DELETE'])
@require_auth
def delete_rule(user, rule_id):
    try:
        with models.db_conn() as db:
            result = db.execute("DELETE FROM rules WHERE id = ? AND user_id = ?", (rule_id, user['id']))
            if result.rowcount == 0:
                return jsonify({"error": "Rule not found"}), 404
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"delete_rule error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/rules/bulk-delete', methods=['POST'])
@require_auth
def bulk_delete_rules(user):
    try:
        data = request.json
        ids = (data or {}).get('ids', [])
        if not ids:
            return jsonify({"error": "No rule IDs provided"}), 400
        if not isinstance(ids, list):
            return jsonify({"error": "ids must be a list"}), 400
        placeholders = ','.join(['?'] * len(ids))
        with models.db_conn() as db:
            db.execute(f"DELETE FROM rules WHERE id IN ({placeholders}) AND user_id = ?",
                       ids + [user['id']])
        return jsonify({"ok": True, "deleted": len(ids)})
    except Exception as e:
        logger.error(f"bulk_delete_rules error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/rules/<int:rule_id>/test-clone', methods=['POST'])
@require_auth
def test_clone_rule(user, rule_id):
    try:
        with models.db_conn() as db:
            r = db.execute("SELECT * FROM rules WHERE id = ? AND user_id = ?",
                           (rule_id, user['id'])).fetchone()
        if not r:
            return jsonify({"error": "Rule not found"}), 404
        with models.db_conn() as db:
            cursor = db.execute(
                """INSERT INTO rules (user_id, name, description, account_id, conditions, actions, status, schedule)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user['id'], f"{r['name']} (Copy)", r['description'], r['account_id'],
                 r['conditions'], r['actions'], 'paused', r['schedule'])
            )
        return jsonify({"ok": True, "id": cursor.lastrowid})
    except Exception as e:
        logger.error(f"test_clone_rule error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/rules/conflicts', methods=['GET'])
@require_auth
def rule_conflicts(user):
    try:
        with models.db_conn() as db:
            rules = db.execute("SELECT * FROM rules WHERE user_id = ? AND status = 'active'",
                               (user['id'],)).fetchall()
        conflicts = []
        rule_list = [dict(r) for r in rules]
        for i, r1 in enumerate(rule_list):
            for r2 in rule_list[i+1:]:
                c1 = json.loads(r1.get('conditions') or '[]')
                c2 = json.loads(r2.get('conditions') or '[]')
                targets1 = set()
                targets2 = set()
                for c in c1:
                    if isinstance(c, dict) and c.get('campaign_id'):
                        targets1.add(c['campaign_id'])
                for c in c2:
                    if isinstance(c, dict) and c.get('campaign_id'):
                        targets2.add(c['campaign_id'])
                if targets1 & targets2:
                    conflicts.append({
                        "rule1": {"id": r1['id'], "name": r1['name']},
                        "rule2": {"id": r2['id'], "name": r2['name']},
                        "overlap": list(targets1 & targets2),
                    })
        return jsonify({"conflicts": conflicts})
    except Exception as e:
        logger.error(f"rule_conflicts error: {e}")
        return jsonify({"conflicts": [], "error": str(e)}), 500

@app.route('/api/rules/emergency-pause-all', methods=['POST'])
@require_auth
def emergency_pause_all(user):
    try:
        with models.db_conn() as db:
            db.execute("UPDATE rules SET status = 'paused', updated_at = datetime('now') WHERE user_id = ?",
                       (user['id'],))
            db.execute("""INSERT INTO bot_actions (user_id, action_type, target_type, details)
                          VALUES (?, 'emergency_pause_all', 'rules', ?)""",
                       (user['id'], json.dumps({"reason": "Manual emergency pause"})))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"emergency_pause_all error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/rules/export', methods=['GET'])
@require_auth
def export_rules(user):
    try:
        account_id = request.args.get('account_id')
        with models.db_conn() as db:
            if account_id:
                rows = db.execute("SELECT * FROM rules WHERE user_id = ? AND account_id = ?",
                                  (user['id'], account_id)).fetchall()
            else:
                rows = db.execute("SELECT * FROM rules WHERE user_id = ?",
                                  (user['id'],)).fetchall()
        rules = []
        for r in rows:
            rules.append({
                "name": r['name'],
                "description": r['description'],
                "conditions": json.loads(r['conditions']) if r['conditions'] else [],
                "actions": json.loads(r['actions']) if r['actions'] else [],
                "schedule": json.loads(r['schedule']) if r['schedule'] else {},
            })
        return jsonify({"rules": rules})
    except Exception as e:
        logger.error(f"export_rules error: {e}")
        return jsonify({"rules": [], "error": str(e)}), 500

@app.route('/api/rules/import', methods=['POST'])
@require_auth
def import_rules(user):
    try:
        data = request.json
        rules = (data or {}).get('rules', [])
        if not isinstance(rules, list):
            return jsonify({"error": "rules must be a list"}), 400
        imported = 0
        for r in rules:
            if not isinstance(r, dict):
                continue
            with models.db_conn() as db:
                db.execute(
                    """INSERT INTO rules (user_id, name, description, account_id, conditions, actions, status, schedule)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (user['id'], r.get('name', 'Imported Rule'), r.get('description', ''),
                     r.get('account_id', ''),
                     json.dumps(r.get('conditions', [])),
                     json.dumps(r.get('actions', [])),
                     'paused',
                     json.dumps(r.get('schedule', {})))
                )
            imported += 1
        return jsonify({"ok": True, "imported": imported})
    except Exception as e:
        logger.error(f"import_rules error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/rules/preview', methods=['POST'])
@require_auth
def preview_rule(user):
    try:
        data = request.json
        conditions = (data or {}).get('conditions', [])
        actions = (data or {}).get('actions', [])
        preview = {
            "conditions_count": len(conditions),
            "actions_count": len(actions),
            "affected_items": [],
            "message": "Preview mode — no changes will be made",
        }
        return jsonify({"preview": preview})
    except Exception as e:
        logger.error(f"preview_rule error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/rules/<int:rule_id>/run', methods=['POST'])
@require_auth
def run_rule_now(user, rule_id):
    """Manually trigger a rule immediately."""
    try:
        with models.db_conn() as db:
            rule = db.execute("SELECT * FROM rules WHERE id = ? AND user_id = ?",
                              (rule_id, user['id'])).fetchone()
        if not rule:
            return jsonify({"error": "Rule not found"}), 404

        results = scheduler.run_rule(rule_id)
        return jsonify({"ok": True, "results": results or []})
    except Exception as e:
        logger.error(f"run_rule_now error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/rules/<int:rule_id>/history', methods=['GET'])
@require_auth
def rule_history(user, rule_id):
    """Get rule execution history from bot_actions."""
    try:
        with models.db_conn() as db:
            rule = db.execute("SELECT * FROM rules WHERE id = ? AND user_id = ?",
                              (rule_id, user['id'])).fetchone()
            if not rule:
                return jsonify({"error": "Rule not found"}), 404

            rows = db.execute(
                """SELECT * FROM bot_actions
                   WHERE rule_id = ? AND user_id = ?
                   ORDER BY created_at DESC LIMIT 50""",
                (rule_id, user['id'])
            ).fetchall()

        history = [{
            "id": r['id'],
            "action_type": r['action_type'],
            "target_type": r['target_type'],
            "target_id": r['target_id'],
            "target_name": r['target_name'],
            "details": json.loads(r['details']) if r['details'] else {},
            "created_at": r['created_at'],
        } for r in rows]

        return jsonify({"history": history, "rule_id": rule_id})
    except Exception as e:
        logger.error(f"rule_history error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scheduler/status', methods=['GET'])
@require_auth
def scheduler_status(user):
    """Get scheduler status and next runs."""
    try:
        status = scheduler.get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"scheduler_status error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Bot Actions API ───

@app.route('/api/bot/actions', methods=['GET'])
@require_auth
def get_bot_actions(user):
    try:
        with models.db_conn() as db:
            rows = db.execute(
                "SELECT * FROM bot_actions WHERE user_id = ? ORDER BY created_at DESC LIMIT 100",
                (user['id'],)
            ).fetchall()
        actions = []
        for r in rows:
            actions.append({
                "id": r['id'],
                "type": r['action_type'],
                "target_type": r['target_type'],
                "target_id": r['target_id'],
                "target_name": r['target_name'],
                "details": json.loads(r['details']) if r['details'] else {},
                "undoable": bool(r['undoable']) and not bool(r['undone']),
                "created_at": r['created_at'],
            })
        return jsonify({"actions": actions})
    except Exception as e:
        logger.error(f"get_bot_actions error: {e}")
        return jsonify({"actions": [], "error": str(e)}), 500

@app.route('/api/bot/actions', methods=['POST'])
@require_auth
def create_bot_action(user):
    try:
        data = request.json
        if not data or not data.get('action_type'):
            return jsonify({"error": "action_type required"}), 400
        with models.db_conn() as db:
            db.execute(
                """INSERT INTO bot_actions (user_id, rule_id, action_type, target_type, target_id, target_name, details)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user['id'], data.get('rule_id'), data['action_type'],
                 data.get('target_type'), data.get('target_id'),
                 data.get('target_name'), json.dumps(data.get('details', {})))
            )
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"create_bot_action error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/bot/actions/<int:action_id>/undo', methods=['POST'])
@require_auth
def undo_bot_action(user, action_id):
    try:
        with models.db_conn() as db:
            action = db.execute("SELECT * FROM bot_actions WHERE id = ? AND user_id = ?",
                               (action_id, user['id'])).fetchone()
            if not action:
                return jsonify({"error": "Action not found"}), 404
            if not action['undoable'] or action['undone']:
                return jsonify({"error": "Action cannot be undone"}), 400
            db.execute("UPDATE bot_actions SET undone = 1 WHERE id = ?", (action_id,))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"undo_bot_action error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Team API ───

@app.route('/api/team/members', methods=['GET'])
@require_auth
def get_team_members(user):
    try:
        with models.db_conn() as db:
            rows = db.execute(
                """SELECT tm.*, u.name, u.email FROM team_members tm
                   JOIN users u ON tm.user_id = u.id
                   WHERE tm.owner_id = ?""",
                (user['id'],)
            ).fetchall()
        members = [{"id": r['id'], "user_id": r['user_id'], "name": r['name'],
                    "email": r['email'], "role": r['role'], "created_at": r['created_at']}
                   for r in rows]
        return jsonify({"members": members})
    except Exception as e:
        logger.error(f"get_team_members error: {e}")
        return jsonify({"members": [], "error": str(e)}), 500

@app.route('/api/team/members/<int:member_id>', methods=['DELETE'])
@require_auth
def remove_team_member(user, member_id):
    try:
        with models.db_conn() as db:
            db.execute("DELETE FROM team_members WHERE id = ? AND owner_id = ?",
                       (member_id, user['id']))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"remove_team_member error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/team/members/<int:member_id>/role', methods=['PUT'])
@require_auth
def update_member_role(user, member_id):
    try:
        data = request.json
        role = (data or {}).get('role', 'viewer')
        if role not in ('admin', 'editor', 'viewer'):
            return jsonify({"error": "Role must be admin, editor, or viewer"}), 400
        with models.db_conn() as db:
            db.execute("UPDATE team_members SET role = ? WHERE id = ? AND owner_id = ?",
                       (role, member_id, user['id']))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"update_member_role error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/team/invites', methods=['GET'])
@require_auth
def get_team_invites(user):
    try:
        with models.db_conn() as db:
            rows = db.execute(
                "SELECT * FROM team_invites WHERE owner_id = ? ORDER BY created_at DESC",
                (user['id'],)
            ).fetchall()
        invites = [{"id": r['id'], "email": r['email'], "role": r['role'],
                    "status": r['status'], "created_at": r['created_at']}
                   for r in rows]
        return jsonify({"invites": invites})
    except Exception as e:
        logger.error(f"get_team_invites error: {e}")
        return jsonify({"invites": [], "error": str(e)}), 500

@app.route('/api/team/invite', methods=['POST'])
@require_auth
def send_invite(user):
    try:
        data = request.json
        email = (data or {}).get('email')
        if not email or '@' not in email:
            return jsonify({"error": "Valid email required"}), 400
        role = data.get('role', 'viewer')
        if role not in ('admin', 'editor', 'viewer'):
            return jsonify({"error": "Role must be admin, editor, or viewer"}), 400
        with models.db_conn() as db:
            db.execute("INSERT INTO team_invites (owner_id, email, role) VALUES (?, ?, ?)",
                       (user['id'], email, role))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"send_invite error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/team/invites/<int:invite_id>', methods=['DELETE'])
@require_auth
def revoke_invite(user, invite_id):
    try:
        with models.db_conn() as db:
            db.execute("DELETE FROM team_invites WHERE id = ? AND owner_id = ?",
                       (invite_id, user['id']))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"revoke_invite error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/team/invite/<int:invite_id>/accept', methods=['POST'])
@require_auth
def accept_invite(user, invite_id):
    try:
        with models.db_conn() as db:
            invite = db.execute("SELECT * FROM team_invites WHERE id = ? AND status = 'pending'",
                               (invite_id,)).fetchone()
            if not invite:
                return jsonify({"error": "Invite not found or already accepted"}), 404
            db.execute("INSERT INTO team_members (owner_id, user_id, role) VALUES (?, ?, ?)",
                       (invite['owner_id'], user['id'], invite['role']))
            db.execute("UPDATE team_invites SET status = 'accepted' WHERE id = ?", (invite_id,))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"accept_invite error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Telegram API ───

@app.route('/api/telegram/status', methods=['GET'])
@require_auth
def telegram_status(user):
    try:
        account_id = request.args.get('account_id')
        with models.db_conn() as db:
            if account_id:
                conn = db.execute(
                    "SELECT * FROM telegram_connections WHERE user_id = ? AND account_id = ?",
                    (user['id'], account_id)
                ).fetchone()
            else:
                conn = db.execute(
                    "SELECT * FROM telegram_connections WHERE user_id = ? LIMIT 1",
                    (user['id'],)
                ).fetchone()
        if conn:
            return jsonify({"connected": bool(conn['connected']), "chat_id": conn['chat_id']})
        return jsonify({"connected": False})
    except Exception as e:
        logger.error(f"telegram_status error: {e}")
        return jsonify({"connected": False, "error": str(e)}), 500

@app.route('/api/telegram/connect', methods=['POST'])
@require_auth
def telegram_connect(user):
    try:
        data = request.json
        bot_token = (data or {}).get('bot_token', '').strip()
        chat_id = (data or {}).get('chat_id', '').strip()
        account_id = data.get('account_id', '')
        if not bot_token or not chat_id:
            return jsonify({"error": "Bot token and chat ID required"}), 400
        with models.db_conn() as db:
            db.execute("DELETE FROM telegram_connections WHERE user_id = ? AND account_id = ?",
                       (user['id'], account_id))
            db.execute("""INSERT INTO telegram_connections (user_id, account_id, chat_id, bot_token, connected)
                          VALUES (?, ?, ?, ?, 1)""",
                       (user['id'], account_id, chat_id, bot_token))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"telegram_connect error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/telegram/disconnect', methods=['POST'])
@require_auth
def telegram_disconnect(user):
    try:
        account_id = request.args.get('account_id', '')
        with models.db_conn() as db:
            db.execute("UPDATE telegram_connections SET connected = 0 WHERE user_id = ? AND account_id = ?",
                       (user['id'], account_id))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"telegram_disconnect error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/telegram/test-send', methods=['POST'])
@require_auth
def telegram_test_send(user):
    try:
        with models.db_conn() as db:
            conn = db.execute(
                "SELECT * FROM telegram_connections WHERE user_id = ? AND connected = 1 LIMIT 1",
                (user['id'],)
            ).fetchone()
        if not conn:
            return jsonify({"error": "Telegram not connected"}), 400
        import requests as req
        resp = req.post(
            f"https://api.telegram.org/bot{conn['bot_token']}/sendMessage",
            json={"chat_id": conn['chat_id'], "text": "🧪 Test message from Acex Ads!"},
            timeout=10
        )
        if resp.status_code == 200:
            return jsonify({"ok": True, "message": "Test message sent!"})
        return jsonify({"error": f"Telegram API error: {resp.text}"}), 400
    except Exception as e:
        logger.error(f"telegram_test_send error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Notifications API ───

@app.route('/api/notifications/settings', methods=['GET'])
@require_auth
def get_notification_settings(user):
    try:
        with models.db_conn() as db:
            s = db.execute("SELECT * FROM notification_settings WHERE user_id = ?",
                           (user['id'],)).fetchone()
        if s:
            return jsonify({
                "email_enabled": bool(s['email_enabled']),
                "telegram_enabled": bool(s['telegram_enabled']),
                "rules_fired": bool(s['rules_fired']),
                "budget_alerts": bool(s['budget_alerts']),
                "daily_summary": bool(s['daily_summary']),
                "settings": json.loads(s['settings_json']) if s['settings_json'] else {},
            })
        return jsonify({
            "email_enabled": True,
            "telegram_enabled": False,
            "rules_fired": True,
            "budget_alerts": True,
            "daily_summary": False,
            "settings": {},
        })
    except Exception as e:
        logger.error(f"get_notification_settings error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/notifications/settings', methods=['PUT'])
@require_auth
def update_notification_settings(user):
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Settings data required"}), 400
        with models.db_conn() as db:
            db.execute("""INSERT OR REPLACE INTO notification_settings
                          (user_id, email_enabled, telegram_enabled, rules_fired, budget_alerts, daily_summary, settings_json)
                          VALUES (?, ?, ?, ?, ?, ?, ?)""",
                       (user['id'],
                        int(data.get('email_enabled', True)),
                        int(data.get('telegram_enabled', False)),
                        int(data.get('rules_fired', True)),
                        int(data.get('budget_alerts', True)),
                        int(data.get('daily_summary', False)),
                        json.dumps(data.get('settings', {}))))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"update_notification_settings error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Tracking API ───

@app.route('/api/track/error', methods=['POST'])
def track_error():
    try:
        data = request.json
        with models.db_conn() as db:
            db.execute("INSERT INTO tracking (event_type, error, user_agent, metadata) VALUES (?, ?, ?, ?)",
                       ('error', (data or {}).get('error', ''), data.get('user_agent', ''),
                        json.dumps(data.get('metadata', {}))))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"track_error error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/track/pageview', methods=['POST'])
def track_pageview():
    try:
        data = request.json
        with models.db_conn() as db:
            db.execute("INSERT INTO tracking (event_type, page, user_agent, metadata) VALUES (?, ?, ?, ?)",
                       ('pageview', (data or {}).get('page', ''), data.get('user_agent', ''),
                        json.dumps(data.get('metadata', {}))))
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"track_pageview error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Announcements API ───

@app.route('/api/announcements/active', methods=['GET'])
def active_announcements():
    return jsonify([])

# ─── AI Post Booster ───

@app.route('/api/ai/post-booster/<ad_id>', methods=['POST'])
@require_auth
def ai_post_booster(user, ad_id):
    try:
        return jsonify({
            "ok": True,
            "suggestion": "AI post booster placeholder — integrate with OpenAI for creative suggestions",
            "ad_id": ad_id,
        })
    except Exception as e:
        logger.error(f"ai_post_booster error: {e}")
        return jsonify({"error": str(e)}), 500

# ─── Health Check ───

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "version": "2.0.0", "timestamp": datetime.now().isoformat()})

# ─── Error Handlers ───

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    migrations.run_migrations()
    logger.info(f"🚀 Acex Ads v2.0 running at http://{config.HOST}:{config.PORT}")
    scheduler.start()
    try:
        app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
    finally:
        scheduler.stop()
