# HANDOFF.md — Facebook Ad Scaler

> **⚠️ อัปเดตทุกครั้งที่มีการเปลี่ยนแปลง — นี่คือ single source of truth สำหรับ agent ถัดไป**

## 📌 Project Overview

**Facebook Ad Scaler** — เครื่องมือจัดการและ scale โฆษณา Facebook อัตโนมัติ

- **Repo:** https://github.com/dmz2001TH/facebook-ad-scaler
- **Tech Stack:** Flask + SQLite + Pre-built React Frontend (static assets)
- **Frontend:** Pre-built React SPA (harvested from Cloudflare Pages), served as static files
- **Font:** Kanit (Thai/English)
- **Port:** 8080
- **Branch:** `master`

---

## 🔄 Workflow (Flow การทำงาน)

```
┌─────────────────────────────────────────────────────────┐
│                    Facebook Ad Scaler                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  React SPA (Frontend)        Flask Backend (app.py)      │
│  ┌──────────────────┐        ┌───────────────────────┐   │
│  │ Static assets     │◄──────│ / & /assets/*          │   │
│  │ (pre-built chunks)│        │                       │   │
│  └──────────────────┘        │  43 API Endpoints     │   │
│                               │  ┌─────────────────┐  │   │
│                               │  │ Auth (5)         │  │   │
│  Browser ────────────────────►│  │ FB API (12)      │  │   │
│  (User)                       │  │ Rules (11)       │  │   │
│                               │  │ AdsGPT (4)       │  │   │
│                               │  │ Bot Actions (3)  │  │   │
│                               │  │ Team (7)         │  │   │
│                               │  │ Telegram (4)     │  │   │
│                               │  │ Notifications(2) │  │   │
│                               │  │ Tracking (2)     │  │   │
│                               │  └─────────────────┘  │   │
│                               └───────────┬───────────┘   │
│                                           │               │
│                               ┌───────────▼───────────┐   │
│                               │ SQLite (scaler.db)     │   │
│                               │ 10 tables              │   │
│                               └───────────────────────┘   │
│                                           │               │
│                               ┌───────────▼───────────┐   │
│                               │ Facebook Marketing API │   │
│                               │ (graph.facebook.com)   │   │
│                               └───────────────────────┘   │
│                                           │               │
│                               ┌───────────▼───────────┐   │
│                               │ Telegram Bot API       │   │
│                               │ (api.telegram.org)     │   │
│                               └───────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ What's Done (สิ่งที่เสร็จแล้ว)

### 1. Backend — Flask App (`app.py`) — 43 API Endpoints ✅

#### Auth System (5 endpoints)
- ✅ `GET /api/auth/me` — Get current user (auto-login first user if no session)
- ✅ `POST /api/auth/register` — Register new user
- ✅ `POST /api/auth/login` — Login with email/password + session
- ✅ `POST /api/auth/logout` — Clear session
- ✅ `GET /api/auth/facebook` — Facebook OAuth placeholder (501 not implemented)

#### Facebook Marketing API Integration (12 endpoints)
- ✅ `POST /api/fb/token` — Save FB access token to user record
- ✅ `GET /api/fb/ad-accounts` — List ad accounts (id, name, status, currency, timezone, business)
- ✅ `GET /api/fb/campaigns` — List campaigns with budget/status info
- ✅ `PUT /api/fb/campaigns/:id/status` — Enable/pause campaign (logs to bot_actions)
- ✅ `PUT /api/fb/campaigns/:id/budget` — Update daily/lifetime budget (logs to bot_actions)
- ✅ `GET /api/fb/adsets` — List ad sets with targeting
- ✅ `GET /api/fb/ads` — List ads with creative
- ✅ `PUT /api/fb/ads/:id/creative` — Update ad creative
- ✅ `GET /api/fb/insights` — Performance insights (impressions, clicks, spend, reach, CTR, CPC, CPM, actions)
- ✅ `GET /api/fb/insights/compare` — Compare last_7d vs last_14d
- ✅ `GET /api/fb/summary` — Account-level summary stats
- ✅ `GET /api/fb/activity` — Activity log from bot_actions table
- ✅ `GET /api/fb/audience` — Audience reach estimate

#### Auto-Rules Engine (11 endpoints)
- ✅ `GET /api/rules` — List all rules
- ✅ `POST /api/rules` — Create rule
- ✅ `GET /api/rules/:id` — Get single rule
- ✅ `PUT /api/rules/:id` — Update rule
- ✅ `DELETE /api/rules/:id` — Delete rule
- ✅ `POST /api/rules/bulk-delete` — Bulk delete by IDs
- ✅ `POST /api/rules/:id/test-clone` — Clone rule (paused)
- ✅ `GET /api/rules/conflicts` — Detect conflicting rules (same campaign targets)
- ✅ `POST /api/rules/emergency-pause-all` — Pause all rules
- ✅ `GET /api/rules/export` — Export rules as JSON
- ✅ `POST /api/rules/import` — Import rules from JSON
- ✅ `POST /api/rules/preview` — Dry run preview

#### AdsGPT — AI Chat (4 endpoints)
- ✅ `GET /api/ads-gpt/conversations` — List conversations
- ✅ `GET /api/ads-gpt/conversations/:id` — Get conversation with messages
- ✅ `DELETE /api/ads-gpt/conversations/:id` — Delete conversation
- ✅ `POST /api/ads-gpt/chat` — Send message & get AI response
- 📝 AI responses are **hardcoded Thai ad expertise** — needs real OpenAI integration

#### Bot Actions — Audit Trail (3 endpoints)
- ✅ `GET /api/bot/actions` — List actions (with undo status)
- ✅ `POST /api/bot/actions` — Create action entry
- ✅ `POST /api/bot/actions/:id/undo` — Mark action as undone

#### Team Management (7 endpoints)
- ✅ `GET /api/team/members` — List team members
- ✅ `DELETE /api/team/members/:id` — Remove member
- ✅ `PUT /api/team/members/:id/role` — Update member role
- ✅ `GET /api/team/invites` — List pending invites
- ✅ `POST /api/team/invite` — Send invite by email
- ✅ `DELETE /api/team/invites/:id` — Revoke invite
- ✅ `POST /api/team/invite/:id/accept` — Accept invite (create team_member)

#### Telegram Notifications (4 endpoints)
- ✅ `GET /api/telegram/status` — Check connection status
- ✅ `POST /api/telegram/connect` — Connect bot (store token + chat_id)
- ✅ `POST /api/telegram/disconnect` — Disconnect
- ✅ `POST /api/telegram/test-send` — Send test message via Telegram API

#### Other (4 endpoints)
- ✅ `GET /api/notifications/settings` — Get notification preferences
- ✅ `PUT /api/notifications/settings` — Update notification preferences
- ✅ `POST /api/track/error` — Track frontend errors
- ✅ `POST /api/track/pageview` — Track page views
- ✅ `GET /api/announcements/active` — Active announcements (returns empty)
- ✅ `POST /api/ai/post-booster/:id` — AI post booster placeholder

### 2. Database Schema (`models.py`) — 10 SQLite Tables ✅

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `users` | User accounts + FB tokens | id, email, password, name, fb_token, role |
| `settings` | Key-value settings per user | user_id, key, value |
| `rules` | Auto-rules engine | id, user_id, name, conditions(JSON), actions(JSON), status, schedule(JSON) |
| `bot_actions` | Audit trail with undo | id, user_id, action_type, target_type, target_id, details(JSON), undoable, undone |
| `conversations` | AdsGPT chat history | id, user_id, title, messages(JSON) |
| `team_members` | Team membership | id, owner_id, user_id, role |
| `team_invites` | Pending invites | id, owner_id, email, role, status |
| `telegram_connections` | Telegram bot config | id, user_id, account_id, chat_id, bot_token, connected |
| `notification_settings` | Per-user notification prefs | user_id, email_enabled, telegram_enabled, rules_fired, budget_alerts, daily_summary |
| `tracking` | Error + pageview tracking | id, event_type, page, error, user_agent, metadata |

### 3. Frontend Assets ✅
- ✅ `templates/index.html` — SPA entry point (4658 bytes)
- ✅ `static/assets/` — 11 pre-built React chunks (~1.5MB total)
  - `index-r215tC_7.js` (main bundle)
  - `index-DnZrT2z0.css` (styles)
  - `Dashboard-JKh4wXFv.js`, `Campaigns-okGSZ_-n.js`, `Rules-DbQk4gH6.js`, `AdsGPT-B_FgLFEi.js`
  - `react-vendor-C0IOBbdh.js`, `CartesianChart-DvZ9Ka_W.js`, `createLucideIcon-CZdZkbWY.js`
  - `rolldown-runtime-S-ySWqyJ.js`, `chart-column-DcT2Lgok.js`

### 4. Tooling ✅
- ✅ `harvester.py` — Downloads frontend assets from Cloudflare Pages
- ✅ `start_scaler.bat` — Windows launcher
- ✅ `.gitignore` — Excludes .db, .log, __pycache__, .env

---

## 📋 What's Next (สิ่งที่ต้องทำต่อ)

### 🔴 Priority 1 — OpenAI Integration for AdsGPT
**Status:** NOT STARTED
- [ ] Replace `generate_ads_gpt_response()` in `app.py` (line ~370) with real OpenAI API calls
- [ ] Add `openai` to requirements / pip install
- [ ] Store OpenAI API key in user settings or .env
- [ ] Add streaming responses (`text/event-stream`) for chat UX
- [ ] Context-aware: pull FB insights data into system prompt so AI can analyze real campaigns

### 🔴 Priority 2 — Rule Execution Engine
**Status:** NOT STARTED
- [ ] Add background scheduler (APScheduler or threading.Timer)
- [ ] Implement rule condition evaluation:
  - Check campaign/adset/ad metrics against conditions
  - Support operators: `>`, `<`, `>=`, `<=`, `==`
  - Support metrics: CPC, CTR, CPM, ROAS, spend, impressions
- [ ] Implement rule action execution:
  - Pause/enable campaigns/adsets/ads
  - Adjust budgets (increase/decrease by % or amount)
  - Send Telegram notifications
- [ ] Update `last_run` and `run_count` after each execution
- [ ] Add execution logs to bot_actions

### 🟡 Priority 3 — Security Hardening
**Status:** NOT STARTED
- [ ] Password hashing (currently stored in plaintext!)
- [ ] CSRF protection
- [ ] Rate limiting on auth endpoints
- [ ] Input validation/sanitization
- [ ] Replace `app.secret_key` with env variable

### 🟡 Priority 4 — Facebook OAuth
**Status:** PLACEHOLDER ONLY
- [ ] Implement full OAuth2 flow in `/api/auth/facebook`
- [ ] Store FB token automatically after OAuth
- [ ] Token refresh mechanism

### 🟢 Priority 5 — Frontend Enhancements
**Status:** NOT STARTED
- [ ] Dark mode support
- [ ] Real-time WebSocket for live data updates
- [ ] PDF report generation
- [ ] Multi-language support (currently Thai-only in AI responses)

### 🟢 Priority 6 — Production Deployment
**Status:** NOT STARTED
- [ ] Replace Flask dev server with Gunicorn/uvicorn
- [ ] Add Dockerfile
- [ ] Environment-based config (dev/staging/prod)
- [ ] Database migrations system
- [ ] Logging framework

---

## 📁 File Structure

```
facebook-ad-scaler/
├── app.py              # Flask app + all 43 API routes (~800 lines)
├── models.py           # SQLite schema (10 tables) + DB helpers (~150 lines)
├── harvester.py        # Asset downloader from CF Pages
├── scaler.db           # SQLite database (auto-created, gitignored)
├── start_scaler.bat    # Windows launcher
├── HANDOFF.md          # THIS FILE — agent handoff doc
├── .gitignore          # Excludes .db, .log, __pycache__, .env
├── scaler_output.log   # Last run log
├── templates/
│   └── index.html      # SPA entry point
└── static/
    └── assets/         # 11 pre-built React chunks (~1.5MB)
```

---

## 🔧 How to Run

```bash
cd facebook-ad-scaler
pip install flask requests
python app.py        # → http://localhost:8080
```

**Requirements:** Python 3.8+, flask, requests
**Optional:** openai (for AdsGPT integration)

---

## 🤖 Agent Handoff Protocol

### How to Continue
1. **Read this file first** — it's the single source of truth
2. **Check git log** — `git log --oneline` for recent changes
3. **Pick from "What's Next"** — work on highest priority unstarted item
4. **Update this file** — mark items done, add notes, update verification log
5. **Commit & push** — `git add -A && git commit -m "..." && git push`

### Key Code Locations
| What | Where | Notes |
|------|-------|-------|
| AI response generation | `app.py` → `generate_ads_gpt_response()` | Replace with OpenAI |
| FB API calls | `app.py` → `fb_api()` helper | Uses requests lib |
| User auth | `app.py` → `get_current_user()` | Session-based, auto-login first user |
| DB schema | `models.py` → `init_db()` | 10 tables, WAL mode |
| Frontend entry | `templates/index.html` | React SPA root |

### Verification Log
| Date | Agent | Action | Notes |
|------|-------|--------|-------|
| 2026-05-14 | OpenClaw | Initial analysis | Mapped 40+ endpoints from frontend JS chunks |
| 2026-05-14 | OpenClaw | Full backend | Implemented all 43 API endpoints, 10 SQLite tables, FB API integration, rules engine, team management, Telegram, AdsGPT chat |
| 2026-05-14 | OpenClaw | Bug fix | Fixed sqlite3.Row .get() bug, tested all 43 endpoints |
| 2026-05-15 | OpenClaw | Handoff update | Comprehensive rewrite of HANDOFF.md with full flow diagram, all endpoints documented, priority list for next agent |

---

## ⚠️ Known Issues & Gotchas

1. **Passwords stored in plaintext** — MUST fix before production
2. **`app.secret_key` hardcoded** — should be from env variable
3. **No CSRF protection** — add before any public deployment
4. **FB token stored in users table** — consider separate secure storage
5. **Auto-login first user** — convenient for dev, remove for production
6. **No error logging framework** — print() only
7. **SQLite** — fine for single-server, migrate to Postgres for scale
