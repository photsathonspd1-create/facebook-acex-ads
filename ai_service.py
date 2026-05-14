"""
OpenAI integration for AdsGPT chat.
Falls back to hardcoded responses if no API key configured.
"""
import json
import logging
import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Facebook Ads expert assistant called AdsGPT. Help users optimize their campaigns, analyze metrics, suggest scaling strategies, and write ad copy.

When given real campaign data, analyze it thoroughly and provide actionable insights.
Always be specific with numbers when possible.
If asked about Thai market specifics, factor in local CPM/CPC benchmarks.

Keep responses concise but thorough. Use markdown formatting for readability."""

# Hardcoded fallback responses
FALLBACK_RESPONSES = {
    'scale': (
        "การ Scale โฆษณา Facebook:\n\n"
        "1. **เพิ่มงบประมาณ** 20-30% ทุก 3-5 วัน (ไม่เกิน 50% ต่อครั้ง)\n"
        "2. **Duplicate Ad Set** ที่ perform ดี แล้วปรับ audience เล็กน้อย\n"
        "3. **ทดสอบ Lookalike** 1%, 3%, 5% จาก purchaser\n"
        "4. **ใช้ CBO** (Campaign Budget Optimization) สำหรับ ad set หลายตัว\n\n"
        "⚠️ ระวัง: ไม่ควรแก้ budget บ่อยเกินไป จะทำให้ algorithm reset"
    ),
    'metrics': (
        "เมตริกสำคัญสำหรับ Facebook Ads:\n\n"
        "- **CPC** (Cost per Click): เป้าหมาย < ฿5-15 สำหรับ TH market\n"
        "- **CTR** (Click-Through Rate): ควร > 1.5-2%\n"
        "- **CPM** (Cost per 1000 Impressions): ขึ้นกับ audience\n"
        "- **ROAS**: เป้าหมาย > 2x สำหรับ e-commerce\n\n"
        "💡 ถ้า CPM สูง ลองเปลี่ยน creative หรือ broad audience"
    ),
    'rule': (
        "การตั้ง Auto-Rules:\n\n"
        "ตัวอย่างกฎที่แนะนำ:\n"
        "1. **ปิด ad** ถ้า CPC > ฿20 หลังใช้งบ > ฿500\n"
        "2. **เพิ่มงบ** 20% ถ้า ROAS > 3x ใน 3 วัน\n"
        "3. **Pause ad set** ถ้า CTR < 0.5% หลัง 1000 impressions\n"
        "4. **แจ้งเตือน** ถ้า daily spend > 150% ของงบปกติ"
    ),
    'default': (
        "สวัสดีครับ! ผมช่วยเรื่อง Facebook Ads ได้:\n\n"
        "📊 **วิเคราะห์** — ดู metrics, หา ad ที่ perform ดี\n"
        "📈 **Scale** — แนะนำวิธีเพิ่มงบ/ขยายผล\n"
        "⚙️ **Auto-Rules** — ตั้งกฎอัตโนมัติ\n"
        "🎯 **Targeting** — แนะนำ audience ที่เหมาะสม\n\n"
        "ลองถามเรื่อง specific ได้เลยครับ!"
    ),
}


def _get_fallback(message: str) -> str:
    msg = message.lower()
    if any(w in msg for w in ['scale', 'เพิ่ม', 'ขยาย', 'budget']):
        return FALLBACK_RESPONSES['scale']
    elif any(w in msg for w in ['cpc', 'cpm', 'ctr', 'cost', 'roas']):
        return FALLBACK_RESPONSES['metrics']
    elif any(w in msg for w in ['rule', 'กฎ', 'auto']):
        return FALLBACK_RESPONSES['rule']
    return FALLBACK_RESPONSES['default']


def _build_context(fb_data: dict = None) -> str:
    if not fb_data:
        return ""
    parts = []
    campaigns = fb_data.get('campaigns', [])
    if campaigns:
        parts.append("Active campaigns:")
        for c in campaigns[:10]:
            parts.append(f"  - {c.get('name', 'N/A')}: status={c.get('status', '?')}, "
                        f"daily_budget={c.get('daily_budget', 'N/A')}")
    insights = fb_data.get('insights', [])
    if insights:
        parts.append("\nRecent insights:")
        for i in insights[:5]:
            parts.append(f"  - spend={i.get('spend', 0)}, ctr={i.get('ctr', 0)}, "
                        f"cpc={i.get('cpc', 0)}, impressions={i.get('impressions', 0)}")
    summary = fb_data.get('summary', {})
    if summary:
        parts.append(f"\nAccount summary: spend={summary.get('spend', 0)}, "
                     f"ctr={summary.get('ctr', 0)}, cpc={summary.get('cpc', 0)}")
    return "\n".join(parts)


def generate_response(message: str, history: list = None, fb_data: dict = None) -> str:
    """Generate AI response. Uses OpenAI if configured, otherwise falls back."""
    api_key = config.OPENAI_API_KEY
    if not api_key:
        logger.info("No OpenAI API key configured, using fallback responses")
        return _get_fallback(message)

    try:
        import openai
        client = openai.OpenAI(api_key=api_key)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        context = _build_context(fb_data)
        if context:
            messages.append({"role": "system", "content": f"Current campaign data:\n{context}"})

        # Add conversation history (last 20 messages max)
        if history:
            for msg in history[-20:]:
                role = msg.get('role', 'user')
                if role in ('user', 'assistant'):
                    messages.append({"role": role, "content": msg.get('content', '')})

        messages.append({"role": "user", "content": message})

        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=messages,
            max_tokens=2000,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except ImportError:
        logger.warning("openai package not installed, using fallback")
        return _get_fallback(message)
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return _get_fallback(message)


def generate_response_stream(message: str, history: list = None, fb_data: dict = None):
    """Generator for streaming responses via SSE."""
    api_key = config.OPENAI_API_KEY
    if not api_key:
        yield f"data: {json.dumps({'content': _get_fallback(message), 'done': True})}\n\n"
        return

    try:
        import openai
        client = openai.OpenAI(api_key=api_key)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        context = _build_context(fb_data)
        if context:
            messages.append({"role": "system", "content": f"Current campaign data:\n{context}"})
        if history:
            for msg in history[-20:]:
                role = msg.get('role', 'user')
                if role in ('user', 'assistant'):
                    messages.append({"role": role, "content": msg.get('content', '')})
        messages.append({"role": "user", "content": message})

        stream = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=messages,
            max_tokens=2000,
            temperature=0.7,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield f"data: {json.dumps({'content': delta.content, 'done': False})}\n\n"
        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
    except ImportError:
        yield f"data: {json.dumps({'content': _get_fallback(message), 'done': True})}\n\n"
    except Exception as e:
        logger.error(f"OpenAI streaming error: {e}")
        yield f"data: {json.dumps({'content': _get_fallback(message), 'done': True})}\n\n"
