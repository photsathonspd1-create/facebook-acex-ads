# HANDOFF.md — Facebook Ad Scaler

> **⚠️ อัปเดตทุกครั้งที่มีการเปลี่ยนแปลง — นี่คือ single source of truth สำหรับ agent ถัดไป**

## 📌 Project Overview

**Facebook Ad Scaler** — เครื่องมือจัดการและ scale โฆษณา Facebook อัตโนมัติ ด้วย AI

- **Repo:** https://github.com/dmz2001TH/facebook-ad-scaler
- **Tech Stack:** Flask + SQLite + Pre-built React Frontend (static assets) + OpenAI
- **Frontend:** Pre-built React SPA (harvested from Cloudflare Pages), served as static files
- **Font:** Kanit (Thai/English)
- **Port:** 8080
- **Branch:** `master`
- **Total API Endpoints:** 70+

---

## 🔄 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Facebook Ad Scaler                       │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  React SPA (Frontend)         Flask Backend (app.py)          │
│  ┌──────────────────┐         ┌───────────────────────────┐   │
│  │ Static assets     │◄───────│ / & /assets/*             │   │
│  │ (pre-built chunks)│         │                           │   │
│  └──────────────────┘         │  70+ API Endpoints        │   │
│                                │  ┌──────────────────────┐ │   │
│  Browser ─────────────────────►│  │ Auth (5)             │ │   │
│  (User)                        │  │ FB API (18)          │ │   │
│                                │  │ Smart Scaling (5)    │ │   │
│  config.py ← .env              │  │ Rules (11)           │ │   │
│  ┌──────────────────┐          │  │ AdsGPT (5)           │ │   │
│  │ SECRET_KEY        │          │  │ Experiments (5)      │ │   │
│  │ OPENAI_API_KEY    │          │  │ Anomaly Detection(1) │ │   │
│  │ DB_PATH           │          │  │ Fatigue Detection(2) │ │   │
│  │ LOG_LEVEL         │          │  │ Budget Pacing (1)    │ │   │
│  └──────────────────┘          │  │ Budget Calendar (1)  │ │   │
│                                │  │ Bot Actions (3)      │ │   │
│                                │  │ Team (7)             │ │   │
│                                │  │ Notifications (6)    │ │   │
│                                │  │ Tracking (2)         │ │   │
│                                │  │ System (3)           │ │   │
│                                │  └──────────────────────┘ │   │
│                                └─────────────┬─────────────┘   │
│                                              │                 │
│                                ┌─────────────▼─────────────┐   │
│                                │ SQLite (scaler.db)         │   │
│                                │ 13 tables                  │   │
│                                └───────────────────────────┘   │
│                                              │                 │
│                    ┌─────────────────────────┼──────────┐      │
│                    ▼                         ▼          ▼      │
│            Facebook Marketing API    OpenAI API   Webhooks    │
│            (graph.facebook.com)     (optional)  TG/Slack/DC   │
└──────────────────────────────────────────────────────────────┘
```

---

## ✅ What's Done (สิ่งที่เสร็จแล้ว)

### 1. Core Backend — Flask App (`app.py`, ~2500 lines)

#### Auth System (5 endpoints) ✅
- `GET /api/auth/me` — Get current user (auto-login first user)
- `POST /api/auth/register` — Register new user
- `POST /api/auth/login` — Login with email/password + session
- `POST /api/auth/logout` — Clear session
- `GET /api/auth/facebook` — Facebook OAuth placeholder (501)

#### Facebook Marketing API (18 endpoints) ✅
- `POST /api/fb/token` — Save FB access token
- `GET /api/fb/ad-accounts` — List all ad accounts
- `GET /api/fb/accounts/compare` — Compare metrics across accounts
- `GET /api/fb/accounts/:id/summary` — Per-account summary
- `GET /api/fb/campaigns` — List campaigns
- `PUT /api/fb/campaigns/:id/status` — Enable/pause campaign
- `PUT /api/fb/campaigns/:id/budget` — Update budget
- `GET /api/fb/adsets` — List ad sets
- `GET /api/fb/ads` — List ads
- `PUT /api/fb/ads/:id/creative` — Update creative
- `GET /api/fb/insights` — Performance insights
- `GET /api/fb/insights/compare` — Compare date ranges
- `GET /api/fb/summary` — Dashboard summary
- `GET /api/fb/activity` — Activity log
- `GET /api/fb/audience` — Audience insights
- `GET /api/fb/pacing` — Budget pacing dashboard
- `GET /api/fb/fatigue` — Creative fatigue detection (all ads)
- `GET /api/fb/fatigue/:id` — Single ad fatigue analysis
- `GET /api/fb/budget-calendar` — Budget change history
- `GET /api/fb/anomalies` — Statistical anomaly detection

#### Smart Scaling Intelligence (5 endpoints) ✅
- `POST /api/scaling/config` — Save scaling config
- `GET /api/scaling/config` — Get scaling config
- `POST /api/scaling/analyze` — Analyze campaigns → recommendations
- `POST /api/scaling/execute` — Execute scaling changes (with confirmation)
- `POST /api/scaling/kill-switch` — Emergency pause all losing campaigns

#### Auto-Rules Engine (11 endpoints) ✅
- Full CRUD + bulk delete, clone, conflict detection
- Emergency pause all, export/import JSON, preview (dry run)

#### AdsGPT — AI Chat (5 endpoints) ✅
- `GET /api/ads-gpt/conversations` — List conversations
- `GET /api/ads-gpt/conversations/:id` — Get conversation
- `DELETE /api/ads-gpt/conversations/:id` — Delete conversation
- `POST /api/ads-gpt/chat` — Chat (OpenAI + streaming SSE + fallback)
- `POST /api/ads-gpt/settings` — Save OpenAI API key

#### A/B Test Tracker (5 endpoints) ✅
- `POST /api/experiments` — Create experiment
- `GET /api/experiments` — List experiments
- `GET /api/experiments/:id` — Get with live FB data comparison
- `POST /api/experiments/:id/conclude` — Declare winner (statistical)
- `DELETE /api/experiments/:id` — Delete experiment

#### Anomaly Detection (1 endpoint) ✅
- Z-score based: flags metrics > 2 std dev from 7-day mean
- Checks CPC, CPM, CTR, spend per campaign

#### Bot Actions — Audit Trail (3 endpoints) ✅
- List, create, undo actions

#### Team Management (7 endpoints) ✅
- Members: list, remove, update role
- Invites: list, send, revoke, accept

#### Notifications (6 endpoints) ✅
- Telegram: status, connect, disconnect, test-send
- Slack/Discord: connect webhook, test-send
- Unified `send_notification()` dispatcher

#### Other (3 endpoints) ✅
- `GET /api/notifications/settings` + `PUT` — Notification prefs
- `POST /api/track/error` + `POST /api/track/pageview` — Tracking
- `GET /api/announcements/active` — Announcements
- `POST /api/ai/post-booster/:id` — AI post booster
- `GET /api/health` — Health check

### 2. Database Schema (`models.py`) — 13 SQLite Tables ✅

| Table | Purpose |
|-------|---------|
| `users` | User accounts + FB tokens |
| `settings` | Key-value settings per user |
| `rules` | Auto-rules engine |
| `bot_actions` | Audit trail with undo |
| `conversations` | AdsGPT chat history |
| `team_members` | Team membership + roles |
| `team_invites` | Pending invites |
| `telegram_connections` | Telegram bot config |
| `notification_channels` | Slack/Discord webhooks |
| `notification_settings` | Per-user notification prefs |
| `tracking` | Error + pageview tracking |
| `scaling_configs` | Smart scaling configuration |
| `experiments` | A/B test experiments |

### 3. AI Service (`ai_service.py`) ✅
- OpenAI integration with streaming (SSE)
- Fallback to hardcoded Thai ad expertise responses
- Context-aware: feeds FB campaign data into prompts

### 4. Config Management (`config.py`) ✅
- Environment-based via `.env` file
- No hardcoded secrets

### 5. Production Files ✅
- `Dockerfile` — Container deployment with health check
- `requirements.txt` — All dependencies
- `test_endpoints.py` — 67/67 tests passing
- `README.md` — Professional documentation
- `.env.example` — Environment template

---

## 📋 What's Next (สิ่งที่ต้องทำต่อ)

### 🔴 Priority 1 — Password Security
- [ ] Hash passwords with bcrypt (currently plaintext!)
- [ ] Add `bcrypt` or `werkzeug.security` to requirements

### 🔴 Priority 2 — Facebook OAuth
- [ ] Implement full OAuth2 flow in `/api/auth/facebook`
- [ ] Store FB token automatically after OAuth
- [ ] Token refresh mechanism

### 🟡 Priority 3 — Background Scheduler
- [ ] APScheduler for rule execution on schedule
- [ ] Auto-scale execution on cron
- [ ] Periodic anomaly scanning

### 🟡 Priority 4 — Production Deployment
- [ ] Replace Flask dev server with Gunicorn
- [ ] HTTPS/TLS setup
- [ ] Rate limiting (flask-limiter)
- [ ] CORS configuration

### 🟢 Priority 5 — Frontend Enhancements
- [ ] Dark mode
- [ ] Real-time WebSocket for live data
- [ ] PDF report generation

---

## 🔧 How to Run

```bash
# Development
pip install -r requirements.txt
cp .env.example .env  # edit as needed
python app.py         # → http://localhost:8080

# Docker
docker build -t ad-scaler .
docker run -p 8080:8080 -v ad-scaler-data:/data ad-scaler

# Tests
python test_endpoints.py
```

---

## 📁 File Structure

```
facebook-ad-scaler/
├── app.py              # Flask app — 70+ API endpoints (~2500 lines)
├── models.py           # SQLite schema (13 tables) + DB helpers
├── ai_service.py       # OpenAI integration + fallback responses
├── config.py           # Environment-based configuration
├── test_endpoints.py   # Endpoint test suite (67 tests)
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container deployment
├── .env.example        # Environment template
├── .gitignore          # Excludes .db, .log, .env, __pycache__
├── HANDOFF.md          # THIS FILE — agent handoff doc
├── README.md           # Project documentation
├── harvester.py        # Asset downloader from CF Pages
├── start_scaler.bat    # Windows launcher
├── templates/
│   └── index.html      # SPA entry point
└── static/
    └── assets/         # 11 pre-built React chunks (~1.5MB)
```

---

## 🤖 Agent Handoff Protocol

### How to Continue
1. **Read this file first** — single source of truth
2. **Check git log** — `git log --oneline` for recent changes
3. **Pick from "What's Next"** — work on highest priority unstarted item
4. **Run tests** — `python test_endpoints.py` must pass 67/67
5. **Update this file** — mark items done, update verification log
6. **Commit & push** — `git add -A && git commit -m "..." && git push`

### Key Code Locations
| What | Where | Notes |
|------|-------|-------|
| AI response generation | `ai_service.py` → `generate_response()` | OpenAI + fallback |
| FB API calls | `app.py` → `fb_api()` helper | Uses requests lib |
| User auth | `app.py` → `get_current_user()` | Session-based |
| Notification dispatch | `app.py` → `send_notification()` | TG/Slack/DC |
| Scaling logic | `app.py` → `analyze_scaling()` | ROAS/CPC/CTR trends |
| Anomaly detection | `app.py` → `detect_anomalies()` | Z-score method |
| Fatigue detection | `app.py` → `fatigue_all()` / `fatigue_single()` | CTR drop analysis |
| DB schema | `models.py` → `init_db()` | 13 tables, WAL mode |
| Config | `config.py` | .env file loader |

### Verification Log
| Date | Agent | Action | Notes |
|------|-------|--------|-------|
| 2026-05-14 | OpenClaw | Initial build | 43 API endpoints, 10 tables |
| 2026-05-14 | OpenClaw | Bug fix | sqlite3.Row .get() bug |
| 2026-05-15 | OpenClaw | v2.0 — Full feature build | +9 features, +3 tables, +30 endpoints, production files |
| 2026-05-15 | OpenClaw | Tests | 67/67 endpoints passing |

---

## ⚠️ Known Issues & Gotchas

1. **Passwords stored in plaintext** — MUST hash before production
2. **No CSRF protection** — add before public deployment
3. **Auto-login first user** — convenient for dev, remove for production
4. **SQLite** — fine for single-server, migrate to Postgres for scale
5. **FB API errors return 200** — wrapped in JSON `{"error": "..."}` not HTTP status
