# Agent Prompt — Acex Ads Project

> Copy prompt นี้แล้วส่งให้ agent ตัวอื่นได้เลย

---

## Prompt สำหรับ Agent

```
คุณเป็น developer agent ที่ต้องทำต่อจาก agent ก่อนหน้าในโปรเจค "Acex Ads" — ระบบจัดการ Facebook Ads

## สิ่งที่ต้องรู้ก่อนเริ่ม

### Repo
- GitHub: https://github.com/photsathonspd1-create/facebook-acex-ads
- Branch: master
- อ่าน HANDOFF.md ก่อนเสมอ — มีข้อมูลครบทุกอย่าง

### สถานะปัจจุบัน
- ระบบทำงานได้แล้ว (tested 50/50 endpoints)
- รันอยู่ที่ port 8080
- มี 84 API routes, 12 DB tables
- Frontend เป็น React pre-built (ไม่มี source code)

### สิ่งที่เสร็จแล้ว (อย่าทำซ้ำ)
1. Security fixes ทั้งหมด (auth bypass, rate limiting, token encryption, session security)
2. Setup page (/setup) — ตั้งค่า Facebook OAuth & OpenAI ผ่าน UI ได้
3. requirements.txt, README.md, .env.example, run.sh
4. crypto.py (Fernet encryption)
5. guide.html, favicon.svg
6. HANDOFF.md

### สิ่งที่ต้องทำต่อ (เรียงตาม priority)

#### Priority: High
1. **Frontend source code** — ตอนนี้มีแค่ compiled JS/CSS ใน static/assets/ ไม่มี source React → ต้องหา source หรือสร้างใหม่ ถ้าจะ modify UI
2. **Production deployment** — เพิ่ม gunicorn, Docker, systemd service, nginx reverse proxy
3. **Long-lived Facebook token** — ตอนนี้ OAuth ได้ short-lived token (~1hr) → ต้องแลกเป็น long-lived token (60 วัน) อัตโนมัติ

#### Priority: Medium
4. **Rate limiting persistent** — ตอนนี้ใช้ in-memory (หายเมื่อ restart) → เปลี่ยนเป็น Redis หรือ SQLite
5. **Token migration** — tokens ที่เก็บก่อนหน้าเป็น plaintext → migrate เข้ารหัส
6. **CSRF protection** — เพิ่ม CSRF token
7. **Test suite** — สร้าง pytest test suite
8. **Error monitoring** — เพิ่ม Sentry หรือ structured logging

#### Priority: Low
9. **OpenAPI/Swagger** — API documentation
10. **Pagination** — บาง endpoint ดึงข้อมูลทั้งหมด
11. **Admin panel** — จัดการ users, view logs
12. **Backup/restore** — SQLite backup strategy
13. **i18n** — รองรับหลายภาษา

### Tech Stack
- Backend: Python 3.12, Flask 3.1, SQLite
- Frontend: React (pre-built in static/assets/)
- AI: OpenAI GPT-4o-mini (optional — has Thai fallback)
- API: Facebook Marketing API v19.0
- Encryption: Fernet (cryptography package)

### วิธีรัน
```bash
cd facebook-acex-ads
pip install -r requirements.txt
cd app && python3 app.py
# เปิด http://localhost:8080
# ตั้งค่าที่ http://localhost:8080/setup
```

### โครงสร้างไฟล์
```
app/
  app.py          — Flask backend (84 routes, ~2800 lines)
  config.py       — Config จาก env vars + auto-generate secrets
  models.py       — SQLite models (12 tables)
  ai_service.py   — OpenAI + fallback responses (Thai)
  scheduler.py    — Background rule scheduler
  migrations.py   — DB migrations
  crypto.py       — Fernet token encryption
static/assets/    — React frontend (compiled)
templates/
  index.html      — SPA entry
  guide.html      — Thai guide
  setup.html      — Setup wizard
```

### Rules
1. อ่าน HANDOFF.md ก่อนเริ่มทำงานเสมอ
2. อัพเดท HANDOFF.md ทุกครั้งที่ทำอะไรเสร็จ
3. ทดสอบก่อน push — รัน server แล้วเทส endpoints
4. Commit message format: `type: description` (feat:, fix:, docs:)
5. Push ขึ้น GitHub หลัง commit ทุกครั้ง
6. อย่าแก้ security rules ใน SOUL.md

### ข้อจำกัด
- ไม่มี frontend source code → ถ้าจะแก้ UI ต้องสร้างหน้า HTML ใหม่ (แบบ setup.html)
- SQLite → ไม่เหมาะกับ concurrent users จำนวนมาก
- Rate limiting in-memory → หายเมื่อ restart
```
