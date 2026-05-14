# HANDOFF.md — Facebook Ad Scaler

> **⚠️ อัปเดตทุกครั้งที่มีการเปลี่ยนแปลง — นี่คือ single source of truth สำหรับ agent ถัดไป**

## 📌 Project Overview

**Facebook Ad Scaler** — เครื่องมือจัดการและ scale โฆษณา Facebook อัตโนมัติ ด้วย AI

- **Repo:** https://github.com/dmz2001TH/facebook-ad-scaler
- **Tech Stack:** Flask + SQLite + OpenAI + React Frontend (static)
- **Port:** 8080
- **Branch:** `master`
- **Total API Endpoints:** 80+
- **DB Tables:** 14
- **Tests:** 79/79 passing ✅

---

## ✅ All Features Complete

### Core Backend (`app.py`, ~2700 lines)

| Category | Endpoints | Status |
|----------|-----------|--------|
| Auth (password hashing + OAuth) | 7 | ✅ |
| Facebook Marketing API | 18 | ✅ |
| Smart Scaling + Kill Switch | 5 | ✅ |
| Rules Engine + Scheduler | 13 | ✅ |
| AdsGPT (OpenAI + streaming) | 5 | ✅ |
| A/B Experiments | 5 | ✅ |
| Anomaly Detection | 1 | ✅ |
| Creative Fatigue | 2 | ✅ |
| Budget Pacing + Calendar | 2 | ✅ |
| Bot Actions (audit trail) | 3 | ✅ |
| Team Management | 7 | ✅ |
| Notifications (TG/Slack/DC) | 6 | ✅ |
| Rate Limiting + CORS | built-in | ✅ |
| Health + System | 3 | ✅ |
| Tracking | 2 | ✅ |

### Production Infrastructure

| File | Purpose | Status |
|------|---------|--------|
| `app.py` | Flask app — 80+ endpoints | ✅ |
| `models.py` | SQLite schema (14 tables) | ✅ |
| `ai_service.py` | OpenAI + fallback responses | ✅ |
| `config.py` | Environment-based config | ✅ |
| `scheduler.py` | Background rule execution | ✅ |
| `migrations.py` | DB migration system | ✅ |
| `gunicorn.conf.py` | Production server config | ✅ |
| `start.sh` | Smart launcher (gunicorn/flask) | ✅ |
| `Dockerfile` | Container deployment | ✅ |
| `test_endpoints.py` | 79/79 tests passing | ✅ |
| `README.md` | Full documentation | ✅ |
| `.env.example` | Config template | ✅ |
| `requirements.txt` | All dependencies | ✅ |

### Security
- ✅ Password hashing (werkzeug.security, pbkdf2)
- ✅ Auto-migration of legacy plaintext passwords
- ✅ Rate limiting (login: 5/60s, API: 100/60s)
- ✅ CORS configurable via env
- ✅ Environment-based secrets (no hardcode)

### AI & Automation
- ✅ AdsGPT with OpenAI (streaming SSE) + fallback
- ✅ Background scheduler (threading.Timer, 60s tick)
- ✅ Rule execution engine (conditions → actions)
- ✅ Anomaly detection (Z-score, 2 std dev)
- ✅ Creative fatigue detection (CTR drop 30%+)
- ✅ Smart scaling analysis (ROAS/CPC/CTR trends)

### Notifications
- ✅ Telegram bot
- ✅ Slack webhooks
- ✅ Discord webhooks
- ✅ Unified dispatcher (`send_notification()`)

---

## 📋 Remaining (Optional Enhancements)

These are NOT blockers — the app is fully functional without them.

### 🟢 Nice-to-Have
- [ ] Facebook OAuth flow (redirect-based, needs FB App ID)
- [ ] Dark mode (frontend)
- [ ] WebSocket for real-time data
- [ ] PDF report generation
- [ ] Multi-language UI
- [ ] PostgreSQL support (for horizontal scale)

---

## 🔧 How to Run

```bash
# Development
pip install -r requirements.txt
cp .env.example .env  # edit as needed
python app.py         # → http://localhost:8080

# Production
pip install -r requirements.txt gunicorn
./start.sh            # auto-detects gunicorn

# Docker
docker build -t ad-scaler .
docker run -p 8080:8080 -v ad-scaler-data:/data ad-scaler

# Tests
python test_endpoints.py  # 79/79 ✅
```

---

## 📁 File Structure

```
facebook-ad-scaler/
├── app.py              # Flask app — 80+ API endpoints (~2700 lines)
├── models.py           # SQLite schema (14 tables)
├── ai_service.py       # OpenAI integration + fallback
├── config.py           # Environment-based configuration
├── scheduler.py        # Background rule execution engine
├── migrations.py       # DB migration system
├── gunicorn.conf.py    # Production server config
├── start.sh            # Smart launcher (gunicorn/flask)
├── test_endpoints.py   # 79 endpoint tests
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container deployment
├── .env.example        # Environment template
├── .gitignore
├── HANDOFF.md          # THIS FILE
├── README.md
├── harvester.py        # Asset downloader
├── start_scaler.bat    # Windows launcher
├── templates/
│   └── index.html      # SPA entry point
└── static/
    └── assets/         # Pre-built React chunks
```

---

## 🤖 Agent Handoff Protocol

1. **Read this file first**
2. **`git log --oneline`** for recent changes
3. **`python test_endpoints.py`** must pass 79/79
4. Pick from "Remaining" if anything left
5. Update this file after changes
6. Commit & push

### Key Code Locations
| What | Where |
|------|-------|
| Password hashing | `app.py` → register/login endpoints |
| OAuth flow | `app.py` → `/api/auth/facebook` + `/callback` |
| Rate limiter | `app.py` → `rate_limit()` decorator |
| CORS | `app.py` → `@app.after_request` |
| Rule scheduler | `scheduler.py` → `start()` / `run_rule()` |
| DB migrations | `migrations.py` → `run_migrations()` |
| AI responses | `ai_service.py` → `generate_response()` |
| Notifications | `app.py` → `send_notification()` |
| Scaling logic | `app.py` → `analyze_scaling()` |
| Anomaly detection | `app.py` → `detect_anomalies()` |

### Verification Log
| Date | Agent | Action | Notes |
|------|-------|--------|-------|
| 2026-05-14 | OpenClaw | v1.0 | 43 endpoints, 10 tables |
| 2026-05-15 | OpenClaw | v2.0 | +9 features, +30 endpoints, production files |
| 2026-05-15 | OpenClaw | v2.1 | Password hashing, OAuth, scheduler, rate limiting, CORS, gunicorn, migrations — 79/79 tests |

---

## ⚠️ Known Issues

1. **SQLite** — fine for single-server, use Postgres for multi-instance
2. **Auto-login first user** — remove for multi-user production
3. **In-memory rate limiter** — resets on restart (use Redis for distributed)
4. **FB OAuth** — needs App ID/Secret to activate
