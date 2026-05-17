"""
Background scheduler for auto-rules execution.
Uses threading.Timer for lightweight scheduling without extra dependencies.
"""
import threading
import json
import logging
import models
from datetime import datetime
import app as flask_app  # Import app to use its fb_api and other helpers

logger = logging.getLogger('scaler.scheduler')

# Global state
_scheduler_running = False
_scheduler_thread = None
_next_runs = {}  # rule_id -> next_run_time string


def check_condition(condition, campaign_data):
    """Check a single condition against campaign data.
    condition format: {"metric": "cpc", "operator": ">", "value": 20}
    """
    metric = condition.get('metric', '')
    operator = condition.get('operator', '>')
    threshold = condition.get('value', 0)
    actual = campaign_data.get(metric, 0)

    try:
        actual = float(actual)
        threshold = float(threshold)
    except (TypeError, ValueError):
        return False

    if operator == '>':
        return actual > threshold
    elif operator == '<':
        return actual < threshold
    elif operator == '>=':
        return actual >= threshold
    elif operator == '<=':
        return actual <= threshold
    elif operator == '==':
        return abs(actual - threshold) < 0.001
    elif operator == '!=':
        return abs(actual - threshold) >= 0.001
    return False


def execute_action(action, user_id, rule_id, rule_name, target_id=None):
    """Execute a single rule action. Returns result dict."""
    action_type = action.get('type', '')
    result = {"action": action_type, "status": "executed"}

    try:
        # Log to bot_actions
        with models.db_conn() as db:
            db.execute(
                """INSERT INTO bot_actions (user_id, rule_id, action_type, target_type, target_id, target_name, details)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, rule_id, f"rule_{action_type}", "campaign", target_id, rule_name,
                 json.dumps(action))
            )

        if action_type == 'notify':
            result["message"] = action.get('message', f'Rule "{rule_name}" triggered')
        elif action_type == 'pause_campaign':
            if target_id:
                # Real FB API call to pause campaign
                resp = flask_app.fb_api(f"{target_id}", method='POST', data={"status": "PAUSED"})
                if 'error' in resp:
                    result["status"] = "error"
                    result["error"] = resp['error']
                else:
                    result["status"] = "success"
            else:
                result["status"] = "error"
                result["error"] = "No campaign ID provided"
        elif action_type == 'adjust_budget':
            change_pct = action.get('change_pct', 0)
            if target_id and change_pct:
                # 1. Fetch current budget
                camp = flask_app.fb_api(f"{target_id}", params={"fields": "daily_budget,lifetime_budget"})
                if 'error' in camp:
                    result["status"] = "error"
                    result["error"] = camp['error']
                else:
                    budget = float(camp.get('daily_budget', camp.get('lifetime_budget', 0)))
                    new_budget = int(budget * (1 + change_pct / 100))
                    # 2. Update budget
                    budget_key = 'daily_budget' if 'daily_budget' in camp else 'lifetime_budget'
                    resp = flask_app.fb_api(f"{target_id}", method='POST', data={budget_key: new_budget})
                    if 'error' in resp:
                        result["status"] = "error"
                        result["error"] = resp['error']
                    else:
                        result["status"] = "success"
                        result["new_budget"] = new_budget
            else:
                result["status"] = "error"
                result["error"] = "Target ID or percentage missing"
        else:
            result["status"] = "error"
            result["error"] = f"Unknown action type: {action_type}"

    except Exception as e:
        logger.error(f"execute_action error: {e}")
        result["status"] = "error"
        result["error"] = str(e)

    return result


def run_rule(rule_id):
    """Execute a single rule — check conditions and fire actions."""
    try:
        with models.db_conn() as db:
            rule = db.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
        if not rule:
            return

        rule = dict(rule)
        if rule['status'] != 'active':
            return

        conditions = json.loads(rule['conditions']) if rule['conditions'] else []
        actions = json.loads(rule['actions']) if rule['actions'] else []
        user_id = rule['user_id']
        account_id = rule['account_id']

        if not account_id:
            logger.warning(f"Rule {rule_id} has no account_id")
            return

        # Fetch real FB metrics for the account/campaigns
        target_campaign_id = None
        for cond in conditions:
            if cond.get('campaign_id'):
                target_campaign_id = cond['campaign_id']
                break
        
        endpoint = f"{target_campaign_id}/insights" if target_campaign_id else f"{account_id}/insights"
        params = {"date_preset": "today", "fields": "cpc,cpm,ctr,spend,actions"}
        
        resp = flask_app.fb_api(endpoint, params=params)
        
        if 'error' in resp or not resp.get('data'):
            logger.error(f"Failed to fetch insights for rule {rule_id}: {resp.get('error', 'No data')}")
            return

        # Extract metrics
        insights = resp['data'][0]
        campaign_data = {
            "cpc": float(insights.get('cpc', 0)),
            "cpm": float(insights.get('cpm', 0)),
            "ctr": float(insights.get('ctr', 0)),
            "spend": float(insights.get('spend', 0)),
        }
        # Add ROAS if possible
        actions_list = insights.get('actions', [])
        purchase_val = sum(float(a.get('value', 0)) for a in actions_list if a.get('action_type') == 'purchase')
        if campaign_data['spend'] > 0:
            campaign_data['roas'] = purchase_val / campaign_data['spend']
        else:
            campaign_data['roas'] = 0

        # Evaluate conditions
        conditions_met = True
        for cond in conditions:
            if not check_condition(cond, campaign_data):
                conditions_met = False
                break

        results = []
        if conditions_met or not conditions:
            for action in actions:
                result = execute_action(action, user_id, rule_id, rule['name'], target_id=target_campaign_id or account_id)
                results.append(result)

        # Update rule last_run and run_count
        with models.db_conn() as db:
            db.execute(
                """UPDATE rules SET last_run = datetime('now'), run_count = run_count + 1,
                   updated_at = datetime('now') WHERE id = ?""",
                (rule_id,)
            )

        logger.info(f"Rule {rule_id} ('{rule['name']}') executed. Results: {len(results)}")
        return results

    except Exception as e:
        logger.error(f"run_rule error for rule {rule_id}: {e}")
        return [{"error": str(e)}]


def _scheduler_tick():
    """Single scheduler tick — check all active rules and run those that are due."""
    global _scheduler_running, _scheduler_thread

    if not _scheduler_running:
        return

    try:
        with models.db_conn() as db:
            rules = db.execute(
                "SELECT * FROM rules WHERE status = 'active'"
            ).fetchall()

        for rule in rules:
            rule = dict(rule)
            schedule = json.loads(rule['schedule']) if rule['schedule'] else {}
            interval_minutes = schedule.get('interval_minutes', 0)

            if interval_minutes <= 0:
                continue

            last_run = rule.get('last_run')
            should_run = False

            if not last_run:
                should_run = True
            else:
                try:
                    last_run_clean = last_run.replace(' ', 'T')
                    last_dt = datetime.fromisoformat(last_run_clean)
                    diff = (datetime.utcnow() - last_dt).total_seconds() / 60
                    if diff >= interval_minutes:
                        should_run = True
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing last_run {last_run}: {e}")
                    should_run = True

            if should_run:
                logger.info(f"Scheduler: Running rule {rule['id']} ('{rule['name']}')")
                run_rule(rule['id'])
                _next_runs[rule['id']] = f"in {interval_minutes} min"
            else:
                if last_run:
                    try:
                        last_run_clean = last_run.replace(' ', 'T')
                        last_dt = datetime.fromisoformat(last_run_clean)
                        next_dt = last_dt.timestamp() + interval_minutes * 60
                        remaining = (next_dt - datetime.utcnow().timestamp()) / 60
                        if remaining > 0:
                            _next_runs[rule['id']] = f"in {remaining:.0f} min"
                    except (ValueError, TypeError):
                        pass

    except Exception as e:
        logger.error(f"Scheduler tick error: {e}")

    # Schedule next tick in 60 seconds
    if _scheduler_running:
        _scheduler_thread = threading.Timer(60.0, _scheduler_tick)
        _scheduler_thread.daemon = True
        _scheduler_thread.start()


def start():
    """Start the background scheduler."""
    global _scheduler_running, _scheduler_thread
    if _scheduler_running:
        logger.warning("Scheduler already running")
        return

    _scheduler_running = True
    logger.info("Background scheduler started")
    _scheduler_tick()


def stop():
    """Stop the background scheduler."""
    global _scheduler_running, _scheduler_thread
    _scheduler_running = False
    if _scheduler_thread:
        _scheduler_thread.cancel()
        _scheduler_thread = None
    logger.info("Background scheduler stopped")


def get_status():
    """Get scheduler status and next runs."""
    global _scheduler_running, _next_runs

    active_rules = []
    try:
        with models.db_conn() as db:
            rows = db.execute(
                "SELECT id, name, schedule, last_run, run_count FROM rules WHERE status = 'active'"
            ).fetchall()
        for r in rows:
            schedule = json.loads(r['schedule']) if r['schedule'] else {}
            active_rules.append({
                "id": r['id'],
                "name": r['name'],
                "interval_minutes": schedule.get('interval_minutes', 0),
                "last_run": r['last_run'],
                "run_count": r['run_count'],
                "next_run": _next_runs.get(r['id'], 'N/A'),
            })
    except Exception as e:
        logger.error(f"get_status error: {e}")

    return {
        "running": _scheduler_running,
        "active_rules": active_rules,
        "total_active": len(active_rules),
    }
