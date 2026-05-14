from flask import Flask, render_template, send_from_directory, jsonify, request, session
import os
import json
import sqlite3
import models
from datetime import datetime

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'SOVEREIGN_KEY_LOTTO'

# ─── Helpers ───

def get_current_user():
    """Get current logged-in user from session."""
    user_id = session.get('user_id')
    if user_id:
        with models.db_conn() as db:
            user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if user:
                return dict(user)
    # Fallback: auto-login first user
    with models.db_conn() as db:
        user = db.execute("SELECT * FROM users LIMIT 1").fetchone()
        if user:
            return dict(user)
    return None

def get_fb_token():
    """Get FB token from current user."""
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
    url = f"https://graph.facebook.com/v19.0/{endpoint}"
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
    except Exception as e:
        return {"error": str(e)}

def require_auth(f):
    """Decorator: require login."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Not authenticated"}), 401
        return f(user, *args, **kwargs)
    return decorated

# ─── Frontend ───

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory('static/assets', path)

# ─── Auth API ───

@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    user = get_current_user()
    if user:
        return jsonify({"user": {
            "id": user['id'],
            "name": user['name'],
            "email": user['email'],
            "role": user.get('role', 'admin')
        }})
    return jsonify({"user": None})

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({"error": "Missing required fields"}), 400
    try:
        with models.db_conn() as db:
            db.execute("INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
                       (data['email'], data['password'], data['name']))
        return jsonify({"ok": True})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already registered"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Missing email or password"}), 400
    with models.db_conn() as db:
        user = db.execute("SELECT * FROM users WHERE email = ? AND password = ?",
                          (data['email'], data['password'])).fetchone()
    if user:
        session['user_id'] = user['id']
        return jsonify({"ok": True, "user": {
            "id": user['id'],
            "name": user['name'],
            "email": user['email'],
            "role": user.get('role', 'admin')
        }})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({"ok": True})

@app.route('/api/auth/facebook', methods=['GET'])
def auth_facebook():
    # Facebook OAuth placeholder
    return jsonify({"error": "Facebook OAuth not configured yet"}), 501

# ─── Settings API ───

@app.route('/api/fb/token', methods=['POST'])
@require_auth
def save_token(user):
    data = request.json
    token = data.get('token', '')
    with models.db_conn() as db:
        db.execute("UPDATE users SET fb_token = ? WHERE id = ?", (token, user['id']))
    return jsonify({"ok": True})

# ─── Facebook API ───

@app.route('/api/fb/ad-accounts', methods=['GET'])
@require_auth
def fb_accounts(user):
    result = fb_api('me/adaccounts', params={
        'fields': 'id,name,account_status,currency,timezone_name,business_name'
    })
    if 'error' in result and 'data' not in result:
        return jsonify({"accounts": [], "error": result['error']})
    accounts = []
    for acc in result.get('data', []):
        status_map = {1: 'ACTIVE', 2: 'DISABLED', 3: 'UNSETTLED', 7: 'PENDING'}
        accounts.append({
            "id": acc['id'],
            "name": acc.get('name', ''),
            "status": status_map.get(acc.get('account_status'), 'UNKNOWN'),
            "currency": acc.get('currency', 'USD'),
            "timezone": acc.get('timezone_name', ''),
            "business": acc.get('business_name', ''),
        })
    return jsonify({"accounts": accounts})

@app.route('/api/fb/campaigns', methods=['GET'])
@require_auth
def fb_campaigns(user):
    account_id = request.args.get('account_id')
    if not account_id:
        # Get first account
        accs = fb_api('me/adaccounts', params={'fields': 'id'})
        data = accs.get('data', [])
        if not data:
            return jsonify({"campaigns": [], "error": "No ad accounts found"})
        account_id = data[0]['id']

    result = fb_api(f'{account_id}/campaigns', params={
        'fields': 'id,name,status,objective,daily_budget,lifetime_budget,created_time,updated_time,stop_times',
        'limit': 100,
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
            "daily_budget": float(c.get('daily_budget', 0)) / 100 if c.get('daily_budget') else None,
            "lifetime_budget": float(c.get('lifetime_budget', 0)) / 100 if c.get('lifetime_budget') else None,
            "created_time": c.get('created_time', ''),
            "updated_time": c.get('updated_time', ''),
        })
    return jsonify({"campaigns": campaigns})

@app.route('/api/fb/campaigns/<campaign_id>/status', methods=['PUT'])
@require_auth
def update_campaign_status(user, campaign_id):
    data = request.json
    status = data.get('status')  # ACTIVE or PAUSED
    result = fb_api(campaign_id, method='POST', data={'status': status})
    if 'error' in result:
        return jsonify(result), 400
    # Log action
    with models.db_conn() as db:
        db.execute("""INSERT INTO bot_actions (user_id, action_type, target_type, target_id, target_name, details)
                      VALUES (?, ?, ?, ?, ?, ?)""",
                   (user['id'], 'campaign_status_change', 'campaign', campaign_id,
                    campaign_id, json.dumps({"new_status": status})))
    return jsonify({"ok": True})

@app.route('/api/fb/campaigns/<campaign_id>/budget', methods=['PUT'])
@require_auth
def update_campaign_budget(user, campaign_id):
    data = request.json
    budget = data.get('budget')
    budget_type = data.get('type', 'daily')  # daily or lifetime
    if not budget:
        return jsonify({"error": "Budget required"}), 400
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

@app.route('/api/fb/adsets', methods=['GET'])
@require_auth
def fb_adsets(user):
    account_id = request.args.get('account_id')
    if not account_id:
        accs = fb_api('me/adaccounts', params={'fields': 'id'})
        data = accs.get('data', [])
        if not data:
            return jsonify({"adsets": []})
        account_id = data[0]['id']
    result = fb_api(f'{account_id}/adsets', params={
        'fields': 'id,name,status,campaign_id,daily_budget,bid_amount,targeting,created_time',
        'limit': 100,
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
            "daily_budget": float(a.get('daily_budget', 0)) / 100 if a.get('daily_budget') else None,
            "bid_amount": a.get('bid_amount'),
            "targeting": a.get('targeting', {}),
            "created_time": a.get('created_time', ''),
        })
    return jsonify({"adsets": adsets})

@app.route('/api/fb/ads', methods=['GET'])
@require_auth
def fb_ads(user):
    account_id = request.args.get('account_id')
    if not account_id:
        accs = fb_api('me/adaccounts', params={'fields': 'id'})
        data = accs.get('data', [])
        if not data:
            return jsonify({"ads": []})
        account_id = data[0]['id']
    result = fb_api(f'{account_id}/ads', params={
        'fields': 'id,name,status,adset_id,creative,created_time',
        'limit': 100,
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

@app.route('/api/fb/ads/<ad_id>/creative', methods=['PUT'])
@require_auth
def update_ad_creative(user, ad_id):
    data = request.json
    result = fb_api(ad_id, method='POST', data={'creative': data})
    if 'error' in result:
        return jsonify(result), 400
    return jsonify({"ok": True})

@app.route('/api/fb/insights', methods=['GET'])
@require_auth
def fb_insights(user):
    account_id = request.args.get('account_id')
    date_preset = request.args.get('date_preset', 'last_7d')
    level = request.args.get('level', 'campaign')
    if not account_id:
        accs = fb_api('me/adaccounts', params={'fields': 'id'})
        data = accs.get('data', [])
        if not data:
            return jsonify({"insights": []})
        account_id = data[0]['id']
    result = fb_api(f'{account_id}/insights', params={
        'fields': 'impressions,clicks,spend,reach,ctr,cpc,cpm,actions,cost_per_action_type',
        'date_preset': date_preset,
        'level': level,
        'limit': 100,
    })
    if 'error' in result and 'data' not in result:
        return jsonify({"insights": [], "error": result['error']})
    insights = []
    for row in result.get('data', []):
        actions = {}
        for a in row.get('actions', []):
            actions[a.get('action_type', '')] = a.get('value', 0)
        insights.append({
            "impressions": int(row.get('impressions', 0)),
            "clicks": int(row.get('clicks', 0)),
            "spend": float(row.get('spend', 0)),
            "reach": int(row.get('reach', 0)),
            "ctr": float(row.get('ctr', 0)),
            "cpc": float(row.get('cpc', 0)),
            "cpm": float(row.get('cpm', 0)),
            "actions": actions,
            "campaign_id": row.get('campaign_id', ''),
            "campaign_name": row.get('campaign_name', ''),
            "adset_id": row.get('adset_id', ''),
            "ad_id": row.get('ad_id', ''),
        })
    return jsonify({"insights": insights})

@app.route('/api/fb/insights/compare', methods=['GET'])
@require_auth
def fb_insights_compare(user):
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

@app.route('/api/fb/summary', methods=['GET'])
@require_auth
def fb_summary(user):
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
            "impressions": int(row.get('impressions', 0)),
            "clicks": int(row.get('clicks', 0)),
            "spend": float(row.get('spend', 0)),
            "reach": int(row.get('reach', 0)),
            "ctr": float(row.get('ctr', 0)),
            "cpc": float(row.get('cpc', 0)),
            "cpm": float(row.get('cpm', 0)),
            "actions": actions,
        }})
    return jsonify({"summary": {}})

@app.route('/api/fb/activity', methods=['GET'])
@require_auth
def fb_activity(user):
    with models.db_conn() as db:
        rows = db.execute(
            "SELECT * FROM bot_actions WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
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
    return jsonify({"activity": actions})

@app.route('/api/fb/audience', methods=['GET'])
@require_auth
def fb_audience(user):
    account_id = request.args.get('account_id')
    if not account_id:
        accs = fb_api('me/adaccounts', params={'fields': 'id'})
        data = accs.get('data', [])
        if not data:
            return jsonify({"audience": {}})
        account_id = data[0]['id']
    # Get reach estimate
    result = fb_api(f'{account_id}/reachestimate', params={
        'targeting_spec': json.dumps({"geo_locations": {"countries": ["TH"]}}),
    })
    return jsonify({"audience": result})

# ─── Rules API ───

@app.route('/api/rules', methods=['GET'])
@require_auth
def get_rules(user):
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

@app.route('/api/rules', methods=['POST'])
@require_auth
def create_rule(user):
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

@app.route('/api/rules/<int:rule_id>', methods=['GET'])
@require_auth
def get_rule(user, rule_id):
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

@app.route('/api/rules/<int:rule_id>', methods=['PUT'])
@require_auth
def update_rule(user, rule_id):
    data = request.json
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

@app.route('/api/rules/<int:rule_id>', methods=['DELETE'])
@require_auth
def delete_rule(user, rule_id):
    with models.db_conn() as db:
        db.execute("DELETE FROM rules WHERE id = ? AND user_id = ?", (rule_id, user['id']))
    return jsonify({"ok": True})

@app.route('/api/rules/bulk-delete', methods=['POST'])
@require_auth
def bulk_delete_rules(user):
    data = request.json
    ids = data.get('ids', [])
    if not ids:
        return jsonify({"error": "No rule IDs provided"}), 400
    placeholders = ','.join(['?'] * len(ids))
    with models.db_conn() as db:
        db.execute(f"DELETE FROM rules WHERE id IN ({placeholders}) AND user_id = ?",
                   ids + [user['id']])
    return jsonify({"ok": True, "deleted": len(ids)})

@app.route('/api/rules/<int:rule_id>/test-clone', methods=['POST'])
@require_auth
def test_clone_rule(user, rule_id):
    with models.db_conn() as db:
        r = db.execute("SELECT * FROM rules WHERE id = ? AND user_id = ?",
                       (rule_id, user['id'])).fetchone()
    if not r:
        return jsonify({"error": "Rule not found"}), 404
    # Clone the rule
    with models.db_conn() as db:
        cursor = db.execute(
            """INSERT INTO rules (user_id, name, description, account_id, conditions, actions, status, schedule)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user['id'], f"{r['name']} (Copy)", r['description'], r['account_id'],
             r['conditions'], r['actions'], 'paused', r['schedule'])
        )
    return jsonify({"ok": True, "id": cursor.lastrowid})

@app.route('/api/rules/conflicts', methods=['GET'])
@require_auth
def rule_conflicts(user):
    with models.db_conn() as db:
        rules = db.execute("SELECT * FROM rules WHERE user_id = ? AND status = 'active'",
                           (user['id'],)).fetchall()
    # Simple conflict detection: rules targeting same campaigns
    conflicts = []
    rule_list = [dict(r) for r in rules]
    for i, r1 in enumerate(rule_list):
        for r2 in rule_list[i+1:]:
            c1 = json.loads(r1.get('conditions') or '[]')
            c2 = json.loads(r2.get('conditions') or '[]')
            # Check if both target same campaigns
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

@app.route('/api/rules/emergency-pause-all', methods=['POST'])
@require_auth
def emergency_pause_all(user):
    with models.db_conn() as db:
        db.execute("UPDATE rules SET status = 'paused', updated_at = datetime('now') WHERE user_id = ?",
                   (user['id'],))
        db.execute("""INSERT INTO bot_actions (user_id, action_type, target_type, details)
                      VALUES (?, 'emergency_pause_all', 'rules', ?)""",
                   (user['id'], json.dumps({"reason": "Manual emergency pause"})))
    return jsonify({"ok": True})

@app.route('/api/rules/export', methods=['GET'])
@require_auth
def export_rules(user):
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
    fmt = request.args.get('format', 'json')
    if fmt == 'json':
        return jsonify({"rules": rules})
    return jsonify({"rules": rules})

@app.route('/api/rules/import', methods=['POST'])
@require_auth
def import_rules(user):
    data = request.json
    rules = data.get('rules', [])
    imported = 0
    for r in rules:
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

@app.route('/api/rules/preview', methods=['POST'])
@require_auth
def preview_rule(user):
    data = request.json
    conditions = data.get('conditions', [])
    actions = data.get('actions', [])
    # Preview what the rule would do (dry run)
    preview = {
        "conditions_count": len(conditions),
        "actions_count": len(actions),
        "affected_items": [],
        "message": "Preview mode — no changes will be made",
    }
    return jsonify({"preview": preview})

# ─── Bot Actions API ───

@app.route('/api/bot/actions', methods=['GET'])
@require_auth
def get_bot_actions(user):
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

@app.route('/api/bot/actions', methods=['POST'])
@require_auth
def create_bot_action(user):
    data = request.json
    with models.db_conn() as db:
        db.execute(
            """INSERT INTO bot_actions (user_id, rule_id, action_type, target_type, target_id, target_name, details)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user['id'], data.get('rule_id'), data['action_type'],
             data.get('target_type'), data.get('target_id'),
             data.get('target_name'), json.dumps(data.get('details', {})))
        )
    return jsonify({"ok": True})

@app.route('/api/bot/actions/<int:action_id>/undo', methods=['POST'])
@require_auth
def undo_bot_action(user, action_id):
    with models.db_conn() as db:
        action = db.execute("SELECT * FROM bot_actions WHERE id = ? AND user_id = ?",
                           (action_id, user['id'])).fetchone()
        if not action:
            return jsonify({"error": "Action not found"}), 404
        if not action['undoable'] or action['undone']:
            return jsonify({"error": "Action cannot be undone"}), 400
        # Mark as undone
        db.execute("UPDATE bot_actions SET undone = 1 WHERE id = ?", (action_id,))
    return jsonify({"ok": True})

# ─── AdsGPT (AI Chat) API ───

@app.route('/api/ads-gpt/conversations', methods=['GET'])
@require_auth
def get_conversations(user):
    with models.db_conn() as db:
        rows = db.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
            (user['id'],)
        ).fetchall()
    convos = [{"id": r['id'], "title": r['title'], "created_at": r['created_at'], "updated_at": r['updated_at']} for r in rows]
    return jsonify({"conversations": convos})

@app.route('/api/ads-gpt/conversations/<int:conv_id>', methods=['GET'])
@require_auth
def get_conversation(user, conv_id):
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

@app.route('/api/ads-gpt/conversations/<int:conv_id>', methods=['DELETE'])
@require_auth
def delete_conversation(user, conv_id):
    with models.db_conn() as db:
        db.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (conv_id, user['id']))
    return jsonify({"ok": True})

@app.route('/api/ads-gpt/chat', methods=['POST'])
@require_auth
def ads_gpt_chat(user):
    data = request.json
    message = data.get('message', '')
    conversation_id = data.get('conversation_id')

    if not message:
        return jsonify({"error": "Message required"}), 400

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

    # Add user message
    messages.append({"role": "user", "content": message, "timestamp": datetime.now().isoformat()})

    # Generate AI response (placeholder - integrate with OpenAI)
    ai_response = generate_ads_gpt_response(message, messages)
    messages.append({"role": "assistant", "content": ai_response, "timestamp": datetime.now().isoformat()})

    # Save conversation
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

def generate_ads_gpt_response(message, history):
    """Generate AI response for ad questions. Replace with OpenAI integration."""
    msg = message.lower()
    if any(w in msg for w in ['scale', 'เพิ่ม', 'ขยาย']):
        return ("การ Scale โฆษณา Facebook:\n\n"
                "1. **เพิ่มงบประมาณ** 20-30% ทุก 3-5 วัน (ไม่เกิน 50% ต่อครั้ง)\n"
                "2. **Duplicate Ad Set** ที่ perform ดี แล้วปรับ audience เล็กน้อย\n"
                "3. **ทดสอบ Lookalike** 1%, 3%, 5% จาก purchaser\n"
                "4. **ใช้ CBO** (Campaign Budget Optimization) สำหรับ ad set หลายตัว\n\n"
                "⚠️ ระวัง: ไม่ควรแก้ budget บ่อยเกินไป จะทำให้ algorithm reset")
    elif any(w in msg for w in ['cpc', 'cpm', 'ctr', 'cost']):
        return ("เมตริกสำคัญสำหรับ Facebook Ads:\n\n"
                "- **CPC** (Cost per Click): เป้าหมาย < ฿5-15 สำหรับ TH market\n"
                "- **CTR** (Click-Through Rate): ควร > 1.5-2%\n"
                "- **CPM** (Cost per 1000 Impressions): ขึ้นกับ audience\n"
                "- **ROAS**: เป้าหมาย > 2x สำหรับ e-commerce\n\n"
                "💡 ถ้า CPM สูง ลองเปลี่ยน creative หรือ broad audience")
    elif any(w in msg for w in ['rule', 'กฎ', 'auto']):
        return ("การตั้ง Auto-Rules:\n\n"
                "ตัวอย่างกฎที่แนะนำ:\n"
                "1. **ปิด ad** ถ้า CPC > ฿20 หลังใช้งบ > ฿500\n"
                "2. **เพิ่มงบ** 20% ถ้า ROAS > 3x ใน 3 วัน\n"
                "3. **Pause ad set** ถ้า CTR < 0.5% หลัง 1000 impressions\n"
                "4. **แจ้งเตือน** ถ้า daily spend > 150% ของงบปกติ")
    else:
        return (f"สวัสดีครับ! ผมช่วยเรื่อง Facebook Ads ได้:\n\n"
                "📊 **วิเคราะห์** — ดู metrics, หา ad ที่ perform ดี\n"
                "📈 **Scale** — แนะนำวิธีเพิ่มงบ/ขยายผล\n"
                "⚙️ **Auto-Rules** — ตั้งกฎอัตโนมัติ\n"
                "🎯 **Targeting** — แนะนำ audience ที่เหมาะสม\n\n"
                "ลองถามเรื่อง specific ได้เลยครับ!")

# ─── Team API ───

@app.route('/api/team/members', methods=['GET'])
@require_auth
def get_team_members(user):
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

@app.route('/api/team/members/<int:member_id>', methods=['DELETE'])
@require_auth
def remove_team_member(user, member_id):
    with models.db_conn() as db:
        db.execute("DELETE FROM team_members WHERE id = ? AND owner_id = ?",
                   (member_id, user['id']))
    return jsonify({"ok": True})

@app.route('/api/team/members/<int:member_id>/role', methods=['PUT'])
@require_auth
def update_member_role(user, member_id):
    data = request.json
    role = data.get('role', 'viewer')
    with models.db_conn() as db:
        db.execute("UPDATE team_members SET role = ? WHERE id = ? AND owner_id = ?",
                   (role, member_id, user['id']))
    return jsonify({"ok": True})

@app.route('/api/team/invites', methods=['GET'])
@require_auth
def get_team_invites(user):
    with models.db_conn() as db:
        rows = db.execute(
            "SELECT * FROM team_invites WHERE owner_id = ? ORDER BY created_at DESC",
            (user['id'],)
        ).fetchall()
    invites = [{"id": r['id'], "email": r['email'], "role": r['role'],
                "status": r['status'], "created_at": r['created_at']}
               for r in rows]
    return jsonify({"invites": invites})

@app.route('/api/team/invite', methods=['POST'])
@require_auth
def send_invite(user):
    data = request.json
    email = data.get('email')
    role = data.get('role', 'viewer')
    if not email:
        return jsonify({"error": "Email required"}), 400
    with models.db_conn() as db:
        db.execute("INSERT INTO team_invites (owner_id, email, role) VALUES (?, ?, ?)",
                   (user['id'], email, role))
    return jsonify({"ok": True})

@app.route('/api/team/invites/<int:invite_id>', methods=['DELETE'])
@require_auth
def revoke_invite(user, invite_id):
    with models.db_conn() as db:
        db.execute("DELETE FROM team_invites WHERE id = ? AND owner_id = ?",
                   (invite_id, user['id']))
    return jsonify({"ok": True})

@app.route('/api/team/invite/<int:invite_id>/accept', methods=['POST'])
@require_auth
def accept_invite(user, invite_id):
    with models.db_conn() as db:
        invite = db.execute("SELECT * FROM team_invites WHERE id = ? AND status = 'pending'",
                           (invite_id,)).fetchone()
        if not invite:
            return jsonify({"error": "Invite not found or already accepted"}), 404
        db.execute("INSERT INTO team_members (owner_id, user_id, role) VALUES (?, ?, ?)",
                   (invite['owner_id'], user['id'], invite['role']))
        db.execute("UPDATE team_invites SET status = 'accepted' WHERE id = ?", (invite_id,))
    return jsonify({"ok": True})

# ─── Telegram API ───

@app.route('/api/telegram/status', methods=['GET'])
@require_auth
def telegram_status(user):
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

@app.route('/api/telegram/connect', methods=['POST'])
@require_auth
def telegram_connect(user):
    data = request.json
    bot_token = data.get('bot_token')
    chat_id = data.get('chat_id')
    account_id = data.get('account_id', '')
    if not bot_token or not chat_id:
        return jsonify({"error": "Bot token and chat ID required"}), 400
    with models.db_conn() as db:
        # Remove existing
        db.execute("DELETE FROM telegram_connections WHERE user_id = ? AND account_id = ?",
                   (user['id'], account_id))
        db.execute("""INSERT INTO telegram_connections (user_id, account_id, chat_id, bot_token, connected)
                      VALUES (?, ?, ?, ?, 1)""",
                   (user['id'], account_id, chat_id, bot_token))
    return jsonify({"ok": True})

@app.route('/api/telegram/disconnect', methods=['POST'])
@require_auth
def telegram_disconnect(user):
    account_id = request.args.get('account_id', '')
    with models.db_conn() as db:
        db.execute("UPDATE telegram_connections SET connected = 0 WHERE user_id = ? AND account_id = ?",
                   (user['id'], account_id))
    return jsonify({"ok": True})

@app.route('/api/telegram/test-send', methods=['POST'])
@require_auth
def telegram_test_send(user):
    with models.db_conn() as db:
        conn = db.execute(
            "SELECT * FROM telegram_connections WHERE user_id = ? AND connected = 1 LIMIT 1",
            (user['id'],)
        ).fetchone()
    if not conn:
        return jsonify({"error": "Telegram not connected"}), 400
    import requests as req
    try:
        resp = req.post(
            f"https://api.telegram.org/bot{conn['bot_token']}/sendMessage",
            json={"chat_id": conn['chat_id'], "text": "🧪 Test message from Ad Scaler!"},
            timeout=10
        )
        if resp.status_code == 200:
            return jsonify({"ok": True, "message": "Test message sent!"})
        return jsonify({"error": f"Telegram API error: {resp.text}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Notifications API ───

@app.route('/api/notifications/settings', methods=['GET'])
@require_auth
def get_notification_settings(user):
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

@app.route('/api/notifications/settings', methods=['PUT'])
@require_auth
def update_notification_settings(user):
    data = request.json
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

# ─── Tracking API ───

@app.route('/api/track/error', methods=['POST'])
def track_error():
    data = request.json
    with models.db_conn() as db:
        db.execute("INSERT INTO tracking (event_type, error, user_agent, metadata) VALUES (?, ?, ?, ?)",
                   ('error', data.get('error', ''), data.get('user_agent', ''),
                    json.dumps(data.get('metadata', {}))))
    return jsonify({"ok": True})

@app.route('/api/track/pageview', methods=['POST'])
def track_pageview():
    data = request.json
    with models.db_conn() as db:
        db.execute("INSERT INTO tracking (event_type, page, user_agent, metadata) VALUES (?, ?, ?, ?)",
                   ('pageview', data.get('page', ''), data.get('user_agent', ''),
                    json.dumps(data.get('metadata', {}))))
    return jsonify({"ok": True})

# ─── Announcements API ───

@app.route('/api/announcements/active', methods=['GET'])
def active_announcements():
    return jsonify([])

# ─── AI Post Booster ───

@app.route('/api/ai/post-booster/<ad_id>', methods=['POST'])
@require_auth
def ai_post_booster(user, ad_id):
    data = request.json
    return jsonify({
        "ok": True,
        "suggestion": "AI post booster placeholder — integrate with OpenAI for creative suggestions",
        "ad_id": ad_id,
    })

if __name__ == "__main__":
    print("🚀 Facebook Ad Scaler running at http://localhost:8080")
    app.run(host='0.0.0.0', port=8080, debug=True)
