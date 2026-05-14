# Facebook Ad Scaler

เครื่องมือจัดการและ scale โฆษณา Facebook อัตโนมัติ ด้วย AI

## Features

### Core
- **Facebook Marketing API** — จัดการ campaigns, ad sets, ads, insights ครบ
- **Smart Scaling** — วิเคราะห์ ROAS/CPC/CTR trend แล้วแนะนำ + execute การ scale อัตโนมัติ
- **Kill Switch** — ปิดทันทีทุก campaign ที่ขาดทุนเกิน threshold
- **Auto-Rules Engine** — ตั้งกฎอัตโนมัติ พร้อม background scheduler รันตาม schedule
- **AdsGPT** — AI chat ช่วยวิเคราะห์โฆษณา (OpenAI streaming + fallback)

### Analytics
- **Creative Fatigue Detection** — ตรวจจับ ad ที่ CTR ลด 30%+ ใน 3 วัน
- **Anomaly Detection** — แจ้งเตือนเมื่อ metrics ผิดปกติ (Z-score, ±2 std dev)
- **Budget Pacing** — ดูว่าวันนี้ใช้ไปเท่าไหร่ เทียบกับเป้า
- **Budget Calendar** — ดูประวัติเปลี่ยนงบ + ผลลัพธ์
- **A/B Test Tracker** — ทำ experiment เปรียบเทียบ ad sets

### Operations
- **Multi-Account** — จัดการหลาย ad accounts + เปรียบเทียบ
- **Team Management** — invite, roles, permissions
- **Notifications** — Telegram, Slack, Discord webhooks
- **Audit Trail** — ทุก action มี log + undo

### Security & Production
- **Password Hashing** — werkzeug.security (pbkdf2)
- **Rate Limiting** — login: 5/60s, API: 100/60s
- **CORS** — configurable via environment
- **DB Migrations** — schema versioning system
- **Gunicorn** — production WSGI server
- **Docker** — container deployment ready

## Quick Start

```bash
# Clone
git clone https://github.com/dmz2001TH/facebook-ad-scaler.git
cd facebook-ad-scaler

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your settings

# Run
python app.py
# → http://localhost:8080
```

## Docker

```bash
docker build -t ad-scaler .
docker run -p 8080:8080 -v ad-scaler-data:/data ad-scaler
```

## Production

```bash
pip install -r requirements.txt gunicorn
./start.sh  # auto-detects gunicorn, falls back to Flask
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `change-me` | Flask secret key |
| `DB_PATH` | `scaler.db` | SQLite database path |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI API key for AdsGPT |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model |
| `FB_APP_ID` | _(empty)_ | Facebook OAuth App ID |
| `FB_APP_SECRET` | _(empty)_ | Facebook OAuth App Secret |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `PORT` | `8080` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level |

## API Endpoints (80+)

| Category | Count | Description |
|----------|-------|-------------|
| Auth | 7 | Login, register, OAuth, session |
| Facebook API | 18 | Campaigns, insights, pacing, fatigue |
| Smart Scaling | 5 | Config, analyze, execute, kill switch |
| Rules + Scheduler | 13 | CRUD, schedule, manual run, history |
| AdsGPT | 5 | Chat, conversations, settings |
| Experiments | 5 | A/B test tracker |
| Notifications | 6 | Telegram, Slack, Discord |
| Team | 7 | Members, invites, roles |
| System | 5 | Health, tracking, announcements |

## Testing

```bash
python test_endpoints.py
# 📊 Results: 79/79 passed, 0 failed
```

## Architecture

```
Browser → Flask (app.py) → SQLite (models.py)
                ↓               ↑
        Facebook API      scheduler.py
        OpenAI API        (background)
        TG/Slack/DC
```

## License

Private — Internal use only
