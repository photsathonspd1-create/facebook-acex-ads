# HANDOFF.md — Acex Ads

> เอกสารสำหรับ Agent คนถัดไป — อ่านก่อนเริ่มทำงานเสมอ

**Last Updated:** 2026-05-17 14:25 GMT+8
**Last Agent:** OpenClaw (main session)
**Repo:** https://github.com/photsathonspd1-create/facebook-acex-ads

---

## 📋 สถานะปัจจุบัน

### ✅ สิ่งที่เสร็จแล้ว (2026-05-17)

#### ความปลอดภัย (Critical Fixes)
- [x] ลบ authentication bypass (`admin@test.com` auto-login)
- [x] Auto-generate `SECRET_KEY` เมื่อไม่ได้ตั้งใน .env
- [x] Session cookie security: HttpOnly, SameSite=Lax, Secure (production)
- [x] Rate limiting: login 5 ครั้ง / 5 นาที ต่อ IP (in-memory)
- [x] เข้ารหัส Facebook token, Telegram bot token, webhook URL ด้วย Fernet (`crypto.py`)
- [x] Constant-time password comparison สำหรับ legacy plaintext
- [x] Input sanitization: strip/lowercase email, validate name length
- [x] Fix circular import ใน `scheduler.py` (lazy import)
- [x] ลบ duplicate error handlers ที่ท้าย `app.py`

#### โครงสร้างโปรเจค
- [x] สร้าง `requirements.txt` (flask, werkzeug, requests, cryptography)
- [x] สร้าง `README.md` (Thai docs, setup guide, API reference)
- [x] สร้าง `.env.example` (ตัวอย่าง config)
- [x] สร้าง `app/crypto.py` (Fernet encryption utility)
- [x] สร้าง `templates/guide.html` (หน้า Guide)
- [x] สร้าง `static/assets/favicon.svg`
- [x] สร้าง `run.sh` (startup script)
- [x] Fix Flask static/template paths (absolute paths)
- [x] Fix `.env` loading จาก project root

#### การทดสอบ (50/50 endpoints ผ่าน)
- [x] Health check, Homepage, Guide, Favicon
- [x] Register, Login, Logout, Session management
- [x] Rate limiting (block ที่ attempt 5)
- [x] Auth validation (duplicate email, short password, bad email)
- [x] Protected endpoints return 401 เมื่อไม่มี session
- [x] Rules CRUD (create, list, get, update, delete, bulk delete, clone, export, import, conflicts, preview)
- [x] Scaling config (save, get)
- [x] Team management (invite, list, members)
- [x] Notifications settings (get, update)
- [x] AdsGPT chat (fallback mode — ไม่มี OpenAI key ยังตอบได้)
- [x] Experiments (create, list)
- [x] Tracking (pageview, error)
- [x] Announcements, AI Post Booster
- [x] Scheduler status
- [x] Emergency pause all
- [x] SPA catch-all routing
- [x] Webhook connect

#### Setup & Configuration (2026-05-17 14:25)
- [x] Setup page (`/setup`) — HTML form สำหรับตั้งค่า Facebook OAuth & OpenAI
- [x] `/api/settings/facebook-oauth` (GET/POST) — ตั้งค่า FB App ID, Secret, Redirect URI ผ่าน UI
- [x] `/api/settings/openai` (GET/POST) — ตั้งค่า OpenAI API Key ผ่าน UI
- [x] Facebook OAuth อ่านค่าจาก DB ก่อน fallback ไป env vars
- [x] App secret ซ่อนใน GET response (แสดงเป็น `***`)
- [x] System check panel ในหน้า Setup (server, auth, FB, OpenAI, scheduler)

---

## 🏗️ โครงสร้างโปรเจค

```
facebook-acex-ads/
├── app/
│   ├── app.py           # Flask backend — 84 routes, ~2700 lines
│   ├── config.py        # Config จาก env vars (+ auto-generate secrets)
│   ├── models.py        # SQLite models, 12 tables
│   ├── ai_service.py    # OpenAI integration + fallback responses (Thai)
│   ├── scheduler.py     # Background rule scheduler (threading.Timer)
│   ├── migrations.py    # DB migrations (version tracking)
│   ├── crypto.py        # Fernet token encryption
│   └── scaler.db        # SQLite database (auto-created)
├── static/assets/       # React frontend (pre-built, ~150 JS/CSS files)
├── templates/
│   ├── index.html       # SPA entry point
│   └── guide.html       # Thai guide page
├── requirements.txt
├── .env.example
├── .gitignore
├── run.sh               # One-command startup
├── README.md
└── HANDOFF.md           # ← เอกสารนี้
```

---

## 🗄️ Database Schema (SQLite)

12 tables ใน `scaler.db`:

| Table | ใช้สำหรับ |
|-------|----------|
| `users` | สมาชิก (email, hashed password, fb_token) |
| `settings` | Key-value settings ต่อ user |
| `rules` | Auto-rules (conditions + actions) |
| `bot_actions` | Audit trail ของ rule executions |
| `conversations` | AdsGPT chat history (JSON messages) |
| `team_members` | ทีมงาน |
| `team_invites` | คำเชิญเข้าทีม |
| `telegram_connections` | Telegram bot connections |
| `notification_settings` | การตั้งค่าแจ้งเตือน |
| `notification_channels` | Slack/Discord webhooks |
| `scaling_configs` | Smart scaling settings |
| `experiments` | A/B test experiments |
| `tracking` | Page view & error tracking |
| `schema_version` | DB migration tracking |

---

## 🔌 API Endpoints (84 routes)

### Auth (6 routes)
```
GET    /api/auth/me
POST   /api/auth/register
POST   /api/auth/login          ← rate limited (5/5min)
POST   /api/auth/logout
GET    /api/auth/facebook       ← OAuth flow
GET    /api/auth/facebook/callback
```

### Facebook Ads (10 routes)
```
GET    /api/fb/ad-accounts
GET    /api/fb/campaigns
PUT    /api/fb/campaigns/<id>/status
PUT    /api/fb/campaigns/<id>/budget
GET    /api/fb/adsets
GET    /api/fb/ads
PUT    /api/fb/ads/<id>/creative
GET    /api/fb/insights
GET    /api/fb/insights/compare
GET    /api/fb/summary
```

### Smart Features (10 routes)
```
POST   /api/scaling/config
GET    /api/scaling/config
POST   /api/scaling/analyze
POST   /api/scaling/execute
POST   /api/scaling/kill-switch
GET    /api/fb/fatigue
GET    /api/fb/fatigue/<ad_id>
GET    /api/fb/pacing
GET    /api/fb/accounts/compare
GET    /api/fb/accounts/<id>/summary
```

### Rules & Automation (12 routes)
```
GET    /api/rules
POST   /api/rules
GET    /api/rules/<id>
PUT    /api/rules/<id>
DELETE /api/rules/<id>
POST   /api/rules/bulk-delete
POST   /api/rules/<id>/test-clone
GET    /api/rules/conflicts
POST   /api/rules/emergency-pause-all
GET    /api/rules/export
POST   /api/rules/import
POST   /api/rules/preview
POST   /api/rules/<id>/run
GET    /api/rules/<id>/history
```

### AdsGPT (5 routes)
```
POST   /api/ads-gpt/settings
GET    /api/ads-gpt/conversations
GET    /api/ads-gpt/conversations/<id>
DELETE /api/ads-gpt/conversations/<id>
POST   /api/ads-gpt/chat        ← supports streaming SSE
```

### Experiments (4 routes)
```
POST   /api/experiments
GET    /api/experiments
GET    /api/experiments/<id>
POST   /api/experiments/<id>/conclude
DELETE /api/experiments/<id>
```

### Notifications (6 routes)
```
POST   /api/notifications/webhook/connect
POST   /api/notifications/webhook/test-send
GET    /api/notifications/settings
PUT    /api/notifications/settings
POST   /api/telegram/connect
POST   /api/telegram/disconnect
POST   /api/telegram/test-send
GET    /api/telegram/status
```

### Team (6 routes)
```
GET    /api/team/members
DELETE /api/team/members/<id>
PUT    /api/team/members/<id>/role
GET    /api/team/invites
POST   /api/team/invite
DELETE /api/team/invites/<id>
POST   /api/team/invite/<id>/accept
```

### Other (7 routes)
```
GET    /api/health
GET    /api/announcements/active
POST   /api/ai/post-booster/<ad_id>
POST   /api/track/pageview
POST   /api/track/error
GET    /api/scheduler/status
GET    /api/fb/activity
GET    /api/fb/budget-calendar
GET    /api/fb/anomalies
GET    /api/fb/audience
POST   /api/bot/actions
POST   /api/bot/actions/<id>/undo
GET    /api/bot/actions
GET    /api/settings/facebook-oauth   ← NEW
POST   /api/settings/facebook-oauth   ← NEW
GET    /api/settings/openai           ← NEW
POST   /api/settings/openai           ← NEW
GET    /
GET    /guide
GET    /setup                         ← NEW
GET    /assets/<path>
GET    /<path>                   ← SPA catch-all
```

---

## ⚙️ Tech Stack

- **Backend:** Python 3.12, Flask 3.1, SQLite
- **Frontend:** React (pre-built in `static/assets/`)
- **AI:** OpenAI GPT-4o-mini (optional — has Thai fallback responses)
- **API:** Facebook Marketing API v19.0
- **Encryption:** Fernet (cryptography package)
- **Scheduling:** threading.Timer (no external deps)
- **Font:** Kanit (Google Fonts)

---

## 🔧 วิธีรัน

```bash
cd facebook-acex-ads
chmod +x run.sh
./run.sh
```

หรือ manual:
```bash
pip install -r requirements.txt
cp .env.example .env
# แก้ SECRET_KEY, ENCRYPTION_KEY ใน .env
cd app && python3 app.py
```

เปิด `http://localhost:8080`

---

## 📝 สิ่งที่ควรทำต่อ (TODO)

### Priority: High
1. **Frontend source code** — ตอนนี้มีแค่ compiled JS/CSS ไม่มี source React → ไม่สามารถ modify UI ได้ ต้องหา source หรือสร้างใหม่
2. **Production deployment** — เพิ่ม gunicorn, nginx, systemd service, Docker
3. **OpenAI streaming** — AdsGPT chat มี streaming endpoint แล้ว แต่ frontend อาจยังไม่รองรับ SSE

### Priority: Medium
4. **Rate limiting แบบ persistent** — ตอนนี้ใช้ in-memory (หายเมื่อ restart) → เปลี่ยนเป็น Redis หรือ SQLite
5. **Token encryption migration** — tokens ที่เก็บก่อนหน้าเป็น plaintext → ต้อง migrate เข้ารหัส
6. **CSRF protection** — เพิ่ม CSRF token สำหรับ form submissions
7. **Logging improvement** — เพิ่ม structured logging (JSON), log rotation
8. **Test suite** — ไม่มี automated tests → สร้าง pytest test suite

### Priority: Low
9. **API documentation** — เพิ่ม OpenAPI/Swagger spec
10. **Pagination** — บาง endpoint ดึงข้อมูลทั้งหมด (limit 500) → เพิ่ม pagination
11. **Admin panel** — จัดการ users, view logs, system health
12. **Backup/restore** — SQLite backup strategy
13. **i18n** — Frontend รองรับหลายภาษา

---

## ⚠️ Known Issues

1. **Rate limit นับรวม login สำเร็จ** — ถ้า login สำเร็จแล้วพยายาม login ซ้ำ จะนับรวม → ไม่ใช่ bug แต่อาจสับสน
2. **Session ไม่ persist ถ้า SECRET_KEY ไม่ได้ตั้ง** — auto-generated key หายเมื่อ restart
3. **Scheduler ไม่ persist** — rules ที่มี `interval_minutes > 0` จะรันตาม schedule แต่ถ้า restart ต้องรอรอบถัดไป
4. **Facebook API errors** — ถ้าไม่มี valid token จะ return error ทุก endpoint ที่เรียก FB API

---

## 🔐 Security Notes

- `.env` อยู่ใน `.gitignore` แล้ว — อย่า commit secrets
- `scaler.db` อยู่ใน `.gitignore` — database มี hashed passwords
- Facebook tokens เข้ารหัสด้วย Fernet (ต้องมี `ENCRYPTION_KEY`)
- Rate limiting เป็น per-IP — ไม่ป้องกัน distributed attacks
- ไม่มี HTTPS enforcement — ต้องทำที่ reverse proxy

---

## 📌 Agent Instructions

1. **อ่าน HANDOFF.md ก่อนเริ่มทำงานเสมอ**
2. **อัพเดท HANDOFF.md ทุกครั้งที่ทำอะไรเสร็จ** — เพิ่มใน ✅ section, อัพเดท TODO
3. **ทดสอบก่อน push** — รัน `python3 app.py` แล้วเทส endpoints
4. **อย่าแก้ security rules** ใน SOUL.md — มีเหตุผลที่ตั้งไว้
5. **Commit message** ใช้ format: `type: description` (e.g., `feat:`, `fix:`, `docs:`)
6. **Push ขึ้น GitHub** หลัง commit ทุกครั้ง
