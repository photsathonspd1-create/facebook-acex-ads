# Acex Ads — Facebook Ad Management

ระบบจัดการ Facebook Ads อัจฉริยะ พร้อม AI Chatbot (AdsGPT), Auto-Rules, Scaling Intelligence, และ Creative Fatigue Detection

## Features

- 📊 **Dashboard** — ดู performance ของ campaigns, ad sets, ads แบบ real-time
- 📈 **Smart Scaling** — วิเคราะห์และแนะนำการเพิ่ม/ลดงบประมาณอัตโนมัติ
- ⚡ **Kill Switch** — ปิด campaign ที่ขาดทุนทันที
- 🎨 **Fatigue Detection** — ตรวจจับโฆษณาที่ creative หมดสภาพ
- 💰 **Budget Pacing** — ติดตามการใช้งบประมาณรายวัน
- 🧪 **A/B Test Tracker** — ติดตามผล experiment ระหว่าง ad sets
- 🤖 **AdsGPT** — AI chatbot ช่วยวิเคราะห์และแนะนำกลยุทธ์ (OpenAI)
- ⚙️ **Auto-Rules** — ตั้งกฎอัตโนมัติ (pause, adjust budget, notify)
- 📢 **Notifications** — เชื่อมต่อ Telegram, Slack, Discord
- 👥 **Team Management** — จัดการทีมและสิทธิ์การเข้าถึง

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/photsathonspd1-create/facebook-acex-ads.git
cd facebook-acex-ads
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# แก้ไขค่าใน .env ตามต้องการ
```

**Environment Variables ที่สำคัญ:**

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | Flask secret key — ใช้ `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ENCRYPTION_KEY` | ✅ | Key สำหรับเข้ารหัส Facebook/Telegram tokens |
| `FB_APP_ID` | สำหรับ OAuth | Facebook App ID |
| `FB_APP_SECRET` | สำหรับ OAuth | Facebook App Secret |
| `FB_REDIRECT_URI` | สำหรับ OAuth | OAuth callback URL |
| `OPENAI_API_KEY` | สำหรับ AdsGPT | OpenAI API key |
| `PORT` | ❌ | Port (default: 8080) |
| `DB_PATH` | ❌ | SQLite database path (default: scaler.db) |

### 3. Run

```bash
cd app
python app.py
```

เปิด browser ไปที่ `http://localhost:8080`

## Production Deployment

```bash
# ใช้ gunicorn แทน development server
pip install gunicorn
cd app
gunicorn -w 4 -b 0.0.0.0:8080 "app:app"
```

**สิ่งที่ต้องทำก่อน deploy จริง:**
1. ตั้ง `SECRET_KEY` เป็นค่า random ที่แข็งแรง
2. ตั้ง `ENCRYPTION_KEY` สำหรับเข้ารหัส tokens
3. ตั้ง `FLASK_DEBUG=false`
4. ใช้ HTTPS (ตั้ง `SESSION_COOKIE_SECURE` จะ auto-enable เมื่อ DEBUG=false)
5. ตั้ง `CORS_ORIGINS` เป็น domain ของคุณ (ไม่ใช่ `*`)

## Project Structure

```
facebook-acex-ads/
├── app/
│   ├── app.py           # Flask backend (API endpoints)
│   ├── config.py        # Configuration from env vars
│   ├── models.py        # SQLite models & DB init
│   ├── ai_service.py    # OpenAI integration (AdsGPT)
│   ├── scheduler.py     # Background rule scheduler
│   ├── migrations.py    # Database migrations
│   ├── crypto.py        # Token encryption utilities
│   └── static/          # Frontend build (React)
├── templates/
│   └── index.html       # SPA entry point
├── requirements.txt
├── .env.example
└── README.md
```

## API Endpoints

### Auth
- `POST /api/auth/register` — สมัครสมาชิก
- `POST /api/auth/login` — เข้าสู่ระบบ
- `POST /api/auth/logout` — ออกจากระบบ
- `GET /api/auth/me` — ข้อมูล user ปัจจุบัน
- `GET /api/auth/facebook` — เริ่ม Facebook OAuth

### Facebook Ads
- `GET /api/fb/ad-accounts` — ดู ad accounts
- `GET /api/fb/campaigns` — ดู campaigns
- `GET /api/fb/insights` — ดู insights/metrics
- `GET /api/fb/summary` — สรุป performance

### Smart Features
- `POST /api/scaling/analyze` — วิเคราะห์ scaling recommendations
- `POST /api/scaling/kill-switch` — Kill switch สำหรับ campaign ขาดทุน
- `GET /api/fb/fatigue` — ตรวจจับ creative fatigue
- `GET /api/fb/pacing` — Budget pacing dashboard
- `GET /api/fb/anomalies` — Anomaly detection

### Rules & Automation
- `GET/POST /api/rules` — จัดการ auto-rules
- `POST /api/rules/<id>/run` — รัน rule ทันที

### AdsGPT
- `POST /api/ads-gpt/chat` — คุยกับ AI (supports streaming)

## Tech Stack

- **Backend:** Python, Flask, SQLite
- **Frontend:** React (pre-built)
- **AI:** OpenAI GPT-4o-mini
- **API:** Facebook Marketing API v19.0

## License

MIT
