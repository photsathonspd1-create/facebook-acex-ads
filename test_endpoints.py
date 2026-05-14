#!/usr/bin/env python3
"""
Facebook Ad Scaler — Endpoint Test Suite
Tests all API endpoints against a running server.
Usage: python test_endpoints.py [--base-url http://localhost:8080]
"""
import sys
import json
import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
session = requests.Session()
passed = 0
failed = 0
errors = []

def test(method, path, data=None, expect_status=None, label=None):
    global passed, failed
    url = f"{BASE_URL}{path}"
    name = label or f"{method} {path}"
    try:
        if method == "GET":
            r = session.get(url, params=data, timeout=10)
        elif method == "POST":
            r = session.post(url, json=data, timeout=10)
        elif method == "PUT":
            r = session.put(url, json=data, timeout=10)
        elif method == "DELETE":
            r = session.delete(url, timeout=10)
        else:
            print(f"  ❌ {name} — unsupported method")
            failed += 1
            return

        if expect_status and r.status_code not in (expect_status if isinstance(expect_status, list) else [expect_status]):
            print(f"  ❌ {name} — expected {expect_status}, got {r.status_code}")
            failed += 1
            errors.append(f"{name}: expected {expect_status}, got {r.status_code}")
            return

        if r.status_code >= 500 and r.status_code != 501:
            print(f"  ❌ {name} — server error {r.status_code}")
            failed += 1
            errors.append(f"{name}: server error {r.status_code}")
            return

        print(f"  ✅ {name} — {r.status_code}")
        passed += 1
    except Exception as e:
        print(f"  ❌ {name} — {e}")
        failed += 1
        errors.append(f"{name}: {e}")


def main():
    global passed, failed
    print(f"\n🧪 Facebook Ad Scaler — Endpoint Tests")
    print(f"   Target: {BASE_URL}\n")

    # ── Health ──
    print("📡 Health & System")
    test("GET", "/api/health", expect_status=200, label="Health check")

    # ── Auth ──
    print("\n🔐 Auth")
    test("GET", "/api/auth/me", expect_status=200, label="Get current user")
    test("POST", "/api/auth/register", data={"email": "test@test.com", "password": "test123", "name": "Test"}, expect_status=[200, 400], label="Register")
    test("POST", "/api/auth/login", data={"email": "test@test.com", "password": "test123"}, expect_status=[200, 401], label="Login")
    test("POST", "/api/auth/logout", expect_status=200, label="Logout")
    test("GET", "/api/auth/facebook", expect_status=501, label="Facebook OAuth placeholder")

    # ── FB Token ──
    print("\n🔑 Facebook Token")
    test("POST", "/api/fb/token", data={"token": "test_token_123"}, expect_status=200, label="Save FB token")

    # ── FB Accounts ──
    print("\n📊 Facebook Accounts")
    test("GET", "/api/fb/ad-accounts", expect_status=200, label="List ad accounts")
    test("GET", "/api/fb/accounts/compare", expect_status=[200, 400], label="Compare accounts")
    test("GET", "/api/fb/accounts/act_123/summary", expect_status=[200, 400], label="Account summary")

    # ── FB Campaigns ──
    print("\n📊 Facebook Campaigns")
    test("GET", "/api/fb/campaigns", expect_status=200, label="List campaigns")
    test("PUT", "/api/fb/campaigns/123/status", data={"status": "PAUSED"}, expect_status=[200, 400], label="Update campaign status")
    test("PUT", "/api/fb/campaigns/123/budget", data={"budget": 100, "type": "daily"}, expect_status=[200, 400], label="Update campaign budget")

    # ── FB Ad Sets & Ads ──
    print("\n📊 Facebook Ad Sets & Ads")
    test("GET", "/api/fb/adsets", expect_status=200, label="List ad sets")
    test("GET", "/api/fb/ads", expect_status=200, label="List ads")
    test("PUT", "/api/fb/ads/123/creative", data={"title": "test"}, expect_status=[200, 400], label="Update ad creative")

    # ── FB Insights ──
    print("\n📊 Facebook Insights")
    test("GET", "/api/fb/insights", expect_status=200, label="Get insights")
    test("GET", "/api/fb/insights/compare", expect_status=200, label="Compare insights")
    test("GET", "/api/fb/summary", expect_status=200, label="Get summary")
    test("GET", "/api/fb/activity", expect_status=200, label="Get activity")
    test("GET", "/api/fb/audience", expect_status=[200, 400], label="Get audience")

    # ── New Features: Scaling ──
    print("\n🧠 Smart Scaling")
    test("POST", "/api/scaling/config", data={"max_budget_increase_pct": 30, "min_roas_threshold": 2.0, "lookback_days": 7, "kill_loss_threshold": 500}, expect_status=200, label="Save scaling config")
    test("GET", "/api/scaling/config", expect_status=200, label="Get scaling config")
    test("POST", "/api/scaling/analyze", data={"account_id": "act_123"}, expect_status=[200, 400], label="Analyze scaling")
    test("POST", "/api/scaling/execute", data={"confirm": False}, expect_status=400, label="Execute scaling (no confirm)")
    test("POST", "/api/scaling/kill-switch", data={"account_id": "act_123"}, expect_status=[200, 400], label="Kill switch")

    # ── New Features: Fatigue ──
    print("\n😴 Creative Fatigue")
    test("GET", "/api/fb/fatigue", expect_status=200, label="Fatigue all ads")
    test("GET", "/api/fb/fatigue/123", expect_status=[200, 400], label="Fatigue single ad")

    # ── New Features: Pacing ──
    print("\n⏱️ Budget Pacing")
    test("GET", "/api/fb/pacing", expect_status=200, label="Budget pacing")

    # ── New Features: Anomalies ──
    print("\n🚨 Anomaly Detection")
    test("GET", "/api/fb/anomalies", expect_status=200, label="Detect anomalies")

    # ── New Features: Budget Calendar ──
    print("\n📅 Budget Calendar")
    test("GET", "/api/fb/budget-calendar", expect_status=200, label="Budget calendar")

    # ── New Features: Experiments ──
    print("\n🧪 A/B Experiments")
    test("POST", "/api/experiments", data={"name": "Test Exp", "variant_a_adset_id": "123", "variant_b_adset_id": "456", "metric": "cpc", "duration_days": 7}, expect_status=200, label="Create experiment")
    test("GET", "/api/experiments", expect_status=200, label="List experiments")
    test("GET", "/api/experiments/1", expect_status=[200, 404], label="Get experiment")
    test("POST", "/api/experiments/1/conclude", expect_status=[200, 404], label="Conclude experiment")
    test("DELETE", "/api/experiments/1", expect_status=[200, 404], label="Delete experiment")

    # ── Rules ──
    print("\n⚙️ Rules Engine")
    test("GET", "/api/rules", expect_status=200, label="List rules")
    test("POST", "/api/rules", data={"name": "Test Rule", "conditions": [], "actions": []}, expect_status=200, label="Create rule")
    test("GET", "/api/rules/1", expect_status=[200, 404], label="Get rule")
    test("PUT", "/api/rules/1", data={"name": "Updated Rule", "conditions": [], "actions": []}, expect_status=[200, 404], label="Update rule")
    test("GET", "/api/rules/conflicts", expect_status=200, label="Rule conflicts")
    test("POST", "/api/rules/preview", data={"conditions": [], "actions": []}, expect_status=200, label="Preview rule")
    test("GET", "/api/rules/export", expect_status=200, label="Export rules")
    test("POST", "/api/rules/import", data={"rules": []}, expect_status=200, label="Import rules")
    test("POST", "/api/rules/emergency-pause-all", expect_status=200, label="Emergency pause all")
    test("POST", "/api/rules/bulk-delete", data={"ids": [999]}, expect_status=200, label="Bulk delete rules")
    test("DELETE", "/api/rules/1", expect_status=[200, 404], label="Delete rule")

    # ── Bot Actions ──
    print("\n🤖 Bot Actions")
    test("GET", "/api/bot/actions", expect_status=200, label="List actions")
    test("POST", "/api/bot/actions", data={"action_type": "test", "target_type": "campaign"}, expect_status=200, label="Create action")

    # ── AdsGPT ──
    print("\n💬 AdsGPT")
    test("GET", "/api/ads-gpt/conversations", expect_status=200, label="List conversations")
    test("POST", "/api/ads-gpt/chat", data={"message": "Hello"}, expect_status=200, label="Chat")
    test("POST", "/api/ads-gpt/settings", data={"openai_api_key": "test"}, expect_status=[200, 404], label="AdsGPT settings")

    # ── Team ──
    print("\n👥 Team")
    test("GET", "/api/team/members", expect_status=200, label="List members")
    test("GET", "/api/team/invites", expect_status=200, label="List invites")
    test("POST", "/api/team/invite", data={"email": "test@test.com", "role": "viewer"}, expect_status=200, label="Send invite")

    # ── Telegram ──
    print("\n📨 Telegram")
    test("GET", "/api/telegram/status", expect_status=200, label="Telegram status")
    test("POST", "/api/telegram/connect", data={"bot_token": "test:token", "chat_id": "123"}, expect_status=200, label="Connect Telegram")
    test("POST", "/api/telegram/disconnect", expect_status=200, label="Disconnect Telegram")
    test("POST", "/api/telegram/test-send", expect_status=[200, 400], label="Test Telegram send")

    # ── Webhooks ──
    print("\n🔔 Webhooks (Slack/Discord)")
    test("POST", "/api/notifications/webhook/connect", data={"webhook_url": "https://hooks.slack.com/test", "webhook_type": "slack"}, expect_status=200, label="Connect Slack webhook")
    test("POST", "/api/notifications/webhook/test-send", data={"channel_id": 1}, expect_status=[200, 400], label="Test webhook")

    # ── Notifications ──
    print("\n🔔 Notifications")
    test("GET", "/api/notifications/settings", expect_status=200, label="Get notification settings")
    test("PUT", "/api/notifications/settings", data={"email_enabled": True, "telegram_enabled": False}, expect_status=200, label="Update notification settings")

    # ── Tracking ──
    print("\n📈 Tracking")
    test("POST", "/api/track/error", data={"error": "test error"}, expect_status=200, label="Track error")
    test("POST", "/api/track/pageview", data={"page": "/dashboard"}, expect_status=200, label="Track pageview")

    # ── Other ──
    print("\n📌 Other")
    test("GET", "/api/announcements/active", expect_status=200, label="Announcements")
    test("POST", "/api/ai/post-booster/123", data={"text": "test"}, expect_status=[200, 400], label="AI post booster")

    # ── Summary ──
    total = passed + failed
    print(f"\n{'='*50}")
    print(f"📊 Results: {passed}/{total} passed, {failed} failed")
    if errors:
        print(f"\n❌ Failures:")
        for e in errors:
            print(f"   - {e}")
    print()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
