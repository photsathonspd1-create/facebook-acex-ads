# 📘 คู่มือการใช้งาน Facebook Ad Scaler

> คู่มือฉบับเต็มสำหรับผู้ใช้งาน — ตั้งแต่เริ่มต้นจนใช้งานจริง

---

## 📑 สารบัญ

1. [เริ่มต้นใช้งาน](#1-เริ่มต้นใช้งาน)
2. [ตั้งค่า Facebook API](#2-ตั้งค่า-facebook-api)
3. [Dashboard ภาพรวม](#3-dashboard-ภาพรวม)
4. [จัดการ Campaigns](#4-จัดการ-campaigns)
5. [Smart Scaling — ระบบ Scale อัจฉริยะ](#5-smart-scaling)
6. [Auto-Rules — กฎอัตโนมัติ](#6-auto-rules)
7. [AdsGPT — AI ช่วยวิเคราะห์](#7-adsgpt)
8. [A/B Test Tracker](#8-ab-test-tracker)
9. [Creative Fatigue Detection](#9-creative-fatigue-detection)
10. [Anomaly Detection](#10-anomaly-detection)
11. [Budget Pacing & Calendar](#11-budget-pacing--calendar)
12. [Notifications — การแจ้งเตือน](#12-notifications)
13. [Team Management](#13-team-management)
14. [ตั้งค่าระบบ](#14-ตั้งค่าระบบ)
15. [Deploy ขึ้น Server จริง](#15-deploy)
16. [FAQ & แก้ปัญหา](#16-faq)

---

## 1. เริ่มต้นใช้งาน

### ติดตั้งบนเครื่อง (Development)

```bash
# 1. Clone โปรเจค
git clone https://github.com/dmz2001TH/facebook-ad-scaler.git
cd facebook-ad-scaler

# 2. ติดตั้ง dependencies
pip install -r requirements.txt

# 3. คัดลอกไฟล์ config
cp .env.example .env

# 4. แก้ไข .env (ดูหัวข้อ "ตั้งค่าระบบ")
nano .env

# 5. รัน
python app.py
```

เปิด browser ไปที่ `http://localhost:8080`

### ติดตั้งด้วย Docker

```bash
docker build -t ad-scaler .
docker run -p 8080:8080 -v ad-scaler-data:/data ad-scaler
```

### ติดตั้งแบบ Production

```bash
pip install -r requirements.txt gunicorn
./start.sh
```

---

## 2. ตั้งค่า Facebook API

### ขั้นตอนที่ 1: สร้าง Facebook App

1. ไปที่ [developers.facebook.com](https://developers.facebook.com)
2. กด **Create App** → เลือก **Business** → ตั้งชื่อ app
3. ไปที่ **Settings > Basic** → จด **App ID** และ **App Secret**

### ขั้นตอนที่ 2: ขอ Permission

1. ไปที่ **App Review > Permissions and Features**
2. ขอ permission ต่อไปนี้:
   - `ads_management` — จัดการโฆษณา
   - `ads_read` — อ่านข้อมูลโฆษณา
   - `business_management` — จัดการ business account
3. เพิ่ม **Marketing API** ใน Products

### ขั้นตอนที่ 3: สร้าง Access Token

วิธีง่ายที่สุด:

1. ไปที่ [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. เลือก app ของคุณ
3. เลือก permission: `ads_management`, `ads_read`
4. กด **Generate Access Token**
5. คัดลอก token มา

> ⚠️ Token แบบนี้อายุสั้น (~1-2 ชม.) สำหรับใช้งานจริง ควรใช้ Long-lived token หรือ System User token

### ขั้นตอนที่ 4: ใส่ Token ในระบบ

1. เปิด Ad Scaler → ไปที่ **Settings**
2. วาง Facebook Access Token ในช่อง **FB Token**
3. กด **Save**

หรือผ่าน API:
```bash
curl -X POST http://localhost:8080/api/fb/token \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_FB_ACCESS_TOKEN"}' \
  -b cookies.txt
```

---

## 3. Dashboard ภาพรวม

Dashboard แสดงข้อมูลสรุปของบัญชีโฆษณา:

- **Total Spend** — งบประมาณที่ใช้ไป (7 วันล่าสุด)
- **Impressions** — จำนวนครั้งที่โฆษณาแสดง
- **Clicks** — จำนวนคลิก
- **CTR** — Click-Through Rate (อัตราคลิก)
- **CPC** — Cost per Click (ราคาต่อคลิก)
- **CPM** — Cost per 1,000 Impressions

### วิธีดู

เปิด browser → `http://localhost:8080` → Dashboard จะโหลดอัตโนมัติ

---

## 4. จัดการ Campaigns

### ดู Campaigns ทั้งหมด

ไปที่เมนู **Campaigns** จะเห็น:
- ชื่อ campaign
- Status (Active / Paused)
- Objective (Conversions, Traffic, etc.)
- Daily Budget

### เปิด / ปิด Campaign

1. เลือก campaign ที่ต้องการ
2. กดปุ่ม **Enable** หรือ **Pause**
3. ระบบจะบันทึก action ไว้ใน audit trail อัตโนมัติ

### เปลี่ยนงบประมาณ

1. เลือก campaign
2. แก้ไข **Daily Budget** หรือ **Lifetime Budget**
3. กด **Save**

> 💡 ระบบจะ log การเปลี่ยนแปลงไว้ใน Budget Calendar อัตโนมัติ

---

## 5. Smart Scaling

ระบบวิเคราะห์และแนะนำการ scale อัตโนมัติ

### ตั้งค่า Scaling Config

ไปที่เมนู **Scaling** หรือผ่าน API:

```bash
curl -X POST http://localhost:8080/api/scaling/config \
  -H "Content-Type: application/json" \
  -d '{
    "max_budget_increase_pct": 30,
    "min_roas_threshold": 2.0,
    "lookback_days": 7,
    "kill_loss_threshold": 500
  }'
```

| Parameter | คำอธิบาย | ค่าแนะนำ |
|-----------|----------|----------|
| `max_budget_increase_pct` | เพิ่มงบได้สูงสุดกี่ % | 20-30% |
| `min_roas_threshold` | ROAS ขั้นต่ำที่จะ scale | 2.0x |
| `lookback_days` | ดูข้อมูลย้อนหลังกี่วัน | 7 วัน |
| `kill_loss_threshold` | ขาดทุนเกินเท่าไหร่ให้ปิด (บาท) | 500 บาท |

### วิเคราะห์

กดปุ่ม **Analyze** หรือ:

```bash
curl -X POST http://localhost:8080/api/scaling/analyze \
  -H "Content-Type: application/json" \
  -d '{"account_id": "act_123456"}'
```

ระบบจะตอบ:
- ✅ **Increase** — campaigns ที่ ROAS ดี แนะนำเพิ่มงบ 20-30%
- ⚠️ **Decrease** — campaigns ที่ ROAS ลดลง แนะนำลดงบ
- 🛑 **Kill** — campaigns ที่ขาดทุนเกิน threshold แนะนำปิด

### Execute การ Scale

หลังดูคำแนะนำแล้ว กด **Execute** เพื่อทำจริง:

```bash
curl -X POST http://localhost:8080/api/scaling/execute \
  -H "Content-Type: application/json" \
  -d '{"confirm": true, "account_id": "act_123456"}'
```

### Kill Switch — ปิดฉุกเฉิน

ถ้าทุกอย่างพัง ต้องปิดทันที:

```bash
curl -X POST http://localhost:8080/api/scaling/kill-switch \
  -H "Content-Type: application/json" \
  -d '{"account_id": "act_123456"}'
```

ระบบจะ pause ทุก campaign ที่กำลังขาดทุนทันที

---

## 6. Auto-Rules

ตั้งกฎให้ระบบทำงานอัตโนมัติ

### สร้าง Rule

ไปที่เมนู **Rules** → กด **Create Rule**

ตัวอย่างกฎ:

#### กฎที่ 1: ปิด Ad ถ้า CPC สูงเกินไป
```
ชื่อ: Pause High CPC
เงื่อนไข: CPC > 20 บาท
การกระทำ: Pause Campaign
Schedule: ทุก 30 นาที
```

#### กฎที่ 2: เพิ่มงบถ้า ROAS ดี
```
ชื่อ: Scale Good ROAS
เงื่อนไข: ROAS > 3.0
การกระทำ: เพิ่มงบ 20%
Schedule: ทุก 3 ชั่วโมง
```

#### กฎที่ 3: แจ้งเตือนถ้า CTR ตก
```
ชื่อ: Low CTR Alert
เงื่อนไข: CTR < 0.5%
การกระทำ: แจ้งเตือน Telegram/Slack
Schedule: ทุก 1 ชั่วโมง
```

### รูปแบบเงื่อนไข (Condition)

```json
{
  "metric": "cpc",
  "operator": ">",
  "value": 20
}
```

| Metric | คำอธิบาย |
|--------|----------|
| `cpc` | Cost per Click |
| `ctr` | Click-Through Rate (%) |
| `cpm` | Cost per 1,000 Impressions |
| `roas` | Return on Ad Spend |
| `spend` | งบที่ใช้ไป |
| `impressions` | จำนวน impressions |

| Operator | คำอธิบาย |
|----------|----------|
| `>` | มากกว่า |
| `<` | น้อยกว่า |
| `>=` | มากกว่าหรือเท่ากับ |
| `<=` | น้อยกว่าหรือเท่ากับ |
| `==` | เท่ากับ |
| `!=` | ไม่เท่ากับ |

### รูปแบบการกระทำ (Action)

```json
{"type": "pause_campaign"}
```
```json
{"type": "adjust_budget", "change_pct": 20}
```
```json
{"type": "adjust_budget", "change_pct": -30}
```
```json
{"type": "notify", "message": "CPC สูงเกินไป!"}
```

### รัน Rule ด้วยมือ

ไปที่ Rule ที่ต้องการ → กด **Run Now**

### ดูประวัติการรัน

ไปที่ Rule → กด **History** หรือ:

```bash
curl http://localhost:8080/api/rules/1/history
```

### Export / Import Rules

```bash
# Export
curl http://localhost:8080/api/rules/export > rules.json

# Import
curl -X POST http://localhost:8080/api/rules/import \
  -H "Content-Type: application/json" \
  -d @rules.json
```

---

## 7. AdsGPT

AI ผู้ช่วยวิเคราะห์โฆษณา

### ใช้งาน

ไปที่เมนู **AdsGPT** → พิมพ์คำถาม

ตัวอย่างคำถามที่ถามได้:

| คำถาม | ระบบจะตอบ |
|-------|-----------|
| "แนะนำวิธี scale ads" | 4 ขั้นตอนการ scale + ข้อควรระวัง |
| "CPC เท่าไหร่ถึงดี?" | เกณฑ์ CPC/CTR/CPM/ROAS สำหรับตลาดไทย |
| "ตั้ง auto-rule ยังไง?" | ตัวอย่างกฎ 4 แบบที่แนะนำ |
| "ad ตัวไหนควรปิด?" | วิเคราะห์จาก metrics (ถ้าต่อ OpenAI) |

### ต่อ OpenAI (ตัวเลือก)

ถ้าต้องการให้ AI ตอบได้ฉลาดขึ้น:

1. ไปที่ `.env` ไฟล์
2. เพิ่ม:
   ```
   OPENAI_API_KEY=sk-your-key-here
   OPENAI_MODEL=gpt-4o-mini
   ```
3. รีสตาร์ท server

> 💡 ถ้าไม่ต่อ OpenAI ระบบจะใช้ fallback responses ที่เขียนไว้ (ภาษาไทย)

### ต่อ OpenAI ผ่าน UI

ไปที่ **Settings** → **AdsGPT Settings** → ใส่ API Key → Save

---

## 8. A/B Test Tracker

เปรียบเทียบ ad sets 2 ตัว ว่าตัวไหนดีกว่า

### สร้าง Experiment

```bash
curl -X POST http://localhost:8080/api/experiments \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Headline A vs B",
    "variant_a_adset_id": "120333000001",
    "variant_b_adset_id": "120333000002",
    "metric": "cpc",
    "duration_days": 7
  }'
```

### ดูผล

ไปที่เมนู **Experiments** → เลือก experiment → ดูผลเปรียบเทียบ:
- CPC ของ A vs B
- CTR ของ A vs B
- Spend ของ A vs B
- ระบบแนะนำ winner

### สรุปผล

เมื่อครบ duration กด **Conclude** → ระบบจะ:
1. ดึงข้อมูลจริงจาก Facebook
2. เปรียบเทียบ metrics
3. Declare winner ตาม statistical significance

---

## 9. Creative Fatigue Detection

ตรวจจับโฆษณาที่ "ตาย" แล้ว (CTR ลดฮวบ)

### วิธีใช้

ไปที่เมนู **Fatigue** หรือ:

```bash
curl http://localhost:8080/api/fb/fatigue
```

### ระบบจะบอก

- **Ad ไหน fatigued** — CTR ลด > 30% ใน 3 วัน เทียบกับ 7-day average
- **Severity** — `warning` (ลด 30-50%) หรือ `critical` (ลด > 50%)
- **Drop %** — ลดลงไปกี่ %
- **Recommendation** — แนะนำให้ทำอะไร (เช่น "เปลี่ยน creative", "pause ad")

### ตัวอย่างผลลัพธ์

```json
{
  "fatigued_ads": [
    {
      "ad_id": "120333000001",
      "ad_name": "Summer Sale - Video A",
      "severity": "critical",
      "ctr_drop_pct": 45.2,
      "recent_ctr": 0.8,
      "baseline_ctr": 1.46,
      "recommendation": "Replace creative immediately — CTR dropped 45%"
    }
  ]
}
```

---

## 10. Anomaly Detection

ตรวจจับ metrics ที่ผิดปกติ (Z-score)

### วิธีใช้

ไปที่เมนู **Anomalies** หรือ:

```bash
curl http://localhost:8080/api/fb/anomalies
```

### ระบบจะตรวจ

- CPC ผิดปกติ (สูงหรือต่ำกว่าปกติ > 2 std dev)
- CPM ผิดปกติ
- CTR ผิดปกติ
- Spend ผิดปกติ

### ตัวอย่างผลลัพธ์

```json
{
  "anomalies": [
    {
      "campaign_name": "Summer Sale",
      "metric": "cpc",
      "actual_value": 35.5,
      "mean": 12.3,
      "std_dev": 8.1,
      "z_score": 2.86,
      "severity": "critical",
      "message": "CPC is 2.86 std devs above normal"
    }
  ]
}
```

---

## 11. Budget Pacing & Calendar

### Budget Pacing

ดูว่าวันนี้ใช้งบไปเท่าไหร่แล้ว:

```bash
curl http://localhost:8080/api/fb/pacing
```

ระบบจะบอกแต่ละ campaign:
- **progress_pct** — ใช้ไปกี่ % ของงบวันนี้
- **pacing_status** — `underspending` / `onschedule` / `overspending`
- **forecast_exhaust_time** — คาดว่าจะหมดงบตอนไหน

### Budget Calendar

ดูประวัติการเปลี่ยนงบ + ผลลัพธ์:

```bash
curl http://localhost:8080/api/fb/budget-calendar
```

จะเห็น:
- วันที่เปลี่ยนงบ
- งบเดิม → งบใหม่
- Spend/ROAS/CPC หลังเปลี่ยน

---

## 12. Notifications

### Telegram

1. สร้าง bot ใน Telegram → คุยกับ @BotFather → `/newbot`
2. ได้ **Bot Token**
3. หา **Chat ID** → ส่งข้อความหา bot แล้วเปิด `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. ใส่ใน Settings

### Slack

1. ไปที่ Slack → **Apps** → **Incoming Webhooks**
2. สร้าง webhook URL
3. ไปที่ Settings → **Connect Webhook** → เลือก Slack → วาง URL

### Discord

1. ไปที่ Discord Channel → **Edit Channel** → **Integrations** → **Webhooks**
2. คัดลอก Webhook URL
3. ไปที่ Settings → **Connect Webhook** → เลือก Discord → วาง URL

### ทดสอบ

กด **Test Send** ใน Settings → ระบบจะส่งข้อความทดสอบไปทุก channel ที่เชื่อมต่อ

---

## 13. Team Management

### เชิญสมาชิก

1. ไปที่เมนู **Team** → **Invite**
2. ใส่ Email + เลือก Role:
   - **Admin** — ทำได้ทุกอย่าง
   - **Editor** — แก้ไข campaigns, rules
   - **Viewer** — ดูอย่างเดียว
3. กด **Send Invite**

### จัดการสมาชิก

- เปลี่ยน Role → กดที่สมาชิก → เลือก Role ใหม่
- ลบสมาชิก → กด **Remove**

---

## 14. ตั้งค่าระบบ

### ไฟล์ `.env`

```bash
# ความปลอดภัย
SECRET_KEY=random-string-at-least-32-chars

# Database
DB_PATH=scaler.db

# Facebook
FB_API_VERSION=v19.0

# Facebook OAuth (ตัวเลือก)
FB_APP_ID=
FB_APP_SECRET=
FB_REDIRECT_URI=http://localhost:8080/api/auth/facebook/callback

# CORS
CORS_ORIGINS=*

# OpenAI (ตัวเลือก)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

# Logging
LOG_LEVEL=INFO
LOG_FILE=scaler.log
```

### สร้าง SECRET_KEY

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

คัดลอกผลลัพธ์ไปใส่ใน `SECRET_KEY`

---

## 15. Deploy

### ด้วย Docker (แนะนำ)

```bash
# Build
docker build -t ad-scaler .

# Run
docker run -d \
  --name ad-scaler \
  -p 8080:8080 \
  -v ad-scaler-data:/data \
  -e SECRET_KEY=your-secret-key \
  -e OPENAI_API_KEY=sk-your-key \
  ad-scaler
```

### ด้วย Gunicorn (บน VPS)

```bash
# ติดตั้ง
pip install -r requirements.txt gunicorn

# ตั้งค่า .env
cp .env.example .env
nano .env

# รัน
./start.sh
```

### ด้วย systemd (รันเป็น service)

สร้างไฟล์ `/etc/systemd/system/ad-scaler.service`:

```ini
[Unit]
Description=Facebook Ad Scaler
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/facebook-ad-scaler
EnvironmentFile=/opt/facebook-ad-scaler/.env
ExecStart=/opt/facebook-ad-scaler/start.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable ad-scaler
sudo systemctl start ad-scaler
sudo systemctl status ad-scaler
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name ads.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 16. FAQ

### Q: ไม่มี Facebook Token ใช้งานได้มั้ย?
**A:** ได้บางส่วน — Dashboard, Rules, Settings ใช้ได้ แต่ข้อมูลจริงจาก Facebook จะไม่แสดง

### Q: OpenAI Key จำเป็นมั้ย?
**A:** ไม่จำเป็น — AdsGPT จะใช้ fallback responses (ภาษาไทย) ถ้าไม่มี key

### Q: ข้อมูลเก็บที่ไหน?
**A:** SQLite database (`scaler.db`) — ไฟล์เดียว ไม่ต้อง setup database server

### Q: รันพร้อมกันหลาย server ได้มั้ย?
**A:** SQLite ไม่รองรับ — ถ้าต้องการหลาย server ต้อง migrate ไป PostgreSQL

### Q: Rate Limit reset ตอนไหน?
**A:** ทุก 60 วินาที (in-memory, reset ถ้า restart server)

### Q: Rule รันอัตโนมัติมั้ย?
**A:** ใช่ — ถ้าตั้ง schedule (interval_minutes) ไว้ scheduler จะรันให้ทุก N นาที

### Q: ดู log ที่ไหน?
**A:** ไฟล์ `scaler.log` หรือดูผ่าน terminal ที่รัน server

### Q: Backup ยังไง?
**A:** copy ไฟล์ `scaler.db` เก็บไว้ (เป็น SQLite เดียว)

```bash
cp scaler.db scaler_backup_$(date +%Y%m%d).db
```

---

## 📞 ต้องการความช่วยเหลือ?

- **GitHub Issues:** https://github.com/dmz2001TH/facebook-ad-scaler/issues
- **API Documentation:** ดู `HANDOFF.md` สำหรับรายการ endpoints ทั้งหมด

---

*Last updated: 2026-05-15*
