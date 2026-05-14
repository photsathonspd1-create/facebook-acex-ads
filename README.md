# Facebook Ad Scaler

เครื่องมือจัดการและ scale โฆษณา Facebook อัตโนมัติ ด้วย AI

## Features

### Core
- **Facebook Marketing API** — จัดการ campaigns, ad sets, ads, insights ครบ
- **Smart Scaling** — วิเคราะห์ ROAS/CPC/CTR trend แล้วแนะนำ + execute การ scale อัตโนมัติ
- **Kill Switch** — ปิดทันทีทุก campaign ที่ขาดทุนเกิน threshold
- **Auto-Rules Engine** — ตั้งกฎอัตโนมัติ (conditions → actions) พร้อม conflict detection
- **AdsGPT** — AI chat ช่วยวิเคราะห์โฆษณา (OpenAI integration + fallback)

### Analytics
- **Creative Fatigue Detection** — ตรวจจับ ad ที่ CTR ลด 30%+ ใน 3 วัน
- **Anomaly Detection** — แจ้งเตือนเมื่อ metrics ผิดปกติ (±2 std dev)
- **Budget Pacing** — ดูว่าวันนี้ใช้งบไปเท่าไหร่ เทียบกับเป้า
- **Budget Calendar** — ดูประวัติเปลี่ยนงบ + ผลลัพธ์
- **A/B Test Tracker** — ทำ experiment เปรียบเทียบ ad sets

### Operations
- **Multi-Account** — จัดการหลาย ad accounts + เปรียบเทียบ
- **Team Management** — invite, roles, permissions
- **Notifications** — Telegram, Slack, Discord webhooks
- **Audit Trail** — ทุก action มี log + undo

## Quick Start

```bash
# Clone
git clone https://github.com/dmz2001TH/facebook-ad-scaler.git
cd facebook-ad-scaler

# Install
pip install -r requirements.txt

# Configure (optional)
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

## Configuration

Copy `.env.example` to `.env` and configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `change-me` | Flask secret key |
| `DB_PATH` | `scaler.db` | SQLite database path |
| `OPENAI_API_KEY` | _(empty)_ | OpenAI API key for AdsGPT |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use |
| `PORT` | `8080` | Server port |
| `LOG_LEVEL` | `INFO` | Logging level |

## API Endpoints (70+)

| Category | Endpoints | Description |
|----------|-----------|-------------|
| Auth | 5 | Login, register, session management |
| Facebook API | 18 | Campaigns, ad sets, ads, insights, pacing |
| Smart Scaling | 5 | Config, analyze, execute, kill switch |
| Rules Engine | 11 | CRUD, conflicts, import/export, emergency |
| AdsGPT | 5 | Chat, conversations, settings |
| Experiments | 5 | A/B test tracker |
| Anomaly Detection | 1 | Statistical anomaly detection |
| Fatigue Detection | 2 | Creative fatigue analysis |
| Budget Calendar | 1 | Budget change history |
| Bot Actions | 3 | Audit trail with undo |
| Team | 7 | Members, invites, roles |
| Notifications | 6 | Telegram, Slack, Discord |
| Tracking | 2 | Errors, pageviews |
| System | 3 | Health, announcements, post booster |

## Architecture

```
Browser → Flask (app.py) → SQLite (models.py)
                ↓
        Facebook Marketing API
        OpenAI API (optional)
        Telegram / Slack / Discord
```

## Testing

```bash
# Start the server
python app.py &

# Run tests
python test_endpoints.py

# Or test against a different URL
python test_endpoints.py https://your-deployed-url.com
```

## File Structure

```
facebook-ad-scaler/
├── app.py              # Flask app — 70+ API endpoints
├── models.py           # SQLite schema (13 tables)
├── ai_service.py       # OpenAI integration + fallback
├── config.py           # Environment-based configuration
├── test_endpoints.py   # Endpoint test suite
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container deployment
├── .env.example        # Environment template
├── .gitignore
├── HANDOFF.md          # Agent handoff documentation
├── templates/
│   └── index.html      # React SPA entry point
└── static/
    └── assets/         # Pre-built React chunks
```

## License

Private — Internal use only
