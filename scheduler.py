"""
Background scheduler for auto-rules execution.
Uses threading.Timer for lightweight scheduling without extra dependencies.
"""
import threading
import json
import logging
import models
from datetime import datetime

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


def execute_action(action, user_id, rule_id, rule_name):
    """Execute a single rule action. Returns result dict."""
    action_type = action.get('type', '')
    result = {"action": action_type, "status": "executed"}

    try:
        # Log to bot_actions
        with models.db_conn() as db:
            db.execute(
                """INSERT INTO bot_actions (user_id, rule_id, action_type, target_type, target_name, details)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, rule_id, f"rule_{action_type}", "rule", rule_name,
                 json.dumps(action))
            )

        if action_type == 'notify':
            result["message"] = action.get('message', f'Rule "{rule_name}" triggered')
            # Notification will be picked up by the app's send_notification
        elif action_type == 'pause_campaign':
            result["note"] = "Campaign pause queued (requires FB API call from app)"
        elif action_type == 'adjust_budget':
            change_pct = action.get('change_pct', 0)
            result["change_pct"] = change_pct
            result["note"] = f"Budget adjustment of {change_pct}% queued"
        else:
            result["note"] = f"Unknown action type: {action_type}"

        result["status"] = "success"
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

        # For each condition, evaluate against a simulated/default data source
        # In production, this would fetch real FB data per campaign
        conditions_met = True
        campaign_data = {}  # Would be populated from FB API in production

        for cond in conditions:
            if not check_condition(cond, campaign_data):
                conditions_met = False
                break

        # If no conditions defined, treat as manual-trigger-only (still execute)
        results = []
        if conditions_met or not conditions:
            for action in actions:
                result = execute_action(action, user_id, rule_id, rule['name'])
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
                    last_dt = datetime.fromisoformat(last_run)
                    diff = (datetime.utcnow() - last_dt).total_seconds() / 60
                    if diff >= interval_minutes:
                        should_run = True
                except (ValueError, TypeError):
                    should_run = True

            if should_run:
                logger.info(f"Scheduler: Running rule {rule['id']} ('{rule['name']}')")
                run_rule(rule['id'])
                _next_runs[rule['id']] = f"in {interval_minutes} min"
            else:
                if last_run:
                    try:
                        last_dt = datetime.fromisoformat(last_run)
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
