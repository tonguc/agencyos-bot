import io

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from arq import ArqRedis

from config import settings
from core.utils import _get_claude_client
from database import get_db
from jobs.pool import get_arq_pool
from repositories.job import JobRepository

router = APIRouter(prefix="/voice", tags=["voice"])

SYSTEM_PROMPT = """Sen AgencyOS'un sesli asistanısın — Türkçe ajans yönetim sistemi için.

GENEL SOHBET:
- "merhaba", "nasılsın", "ne yaparsın" gibi mesajlara sıcak, kısa cevap ver
- AgencyOS'u tanıtabilirsin: lead bulur, audit yapar, teklif hazırlar
- Her mesaj aramaya dönüştürme. Sohbet et.

ARAMA AKIŞI — sadece kullanıcı "ara", "bul", "tara", "bak" dediğinde:
1. Mesajda şehir + ne aranacağı varsa → HEMEN tool'u çağır, soru sorma
2. Sadece şehir eksikse → "Hangi şehirde?" diye sor (başka soru sorma)
3. Hem şehir hem konu eksikse → "Ne arıyoruz, hangi şehirde?"
4. Onay (evet/başlat/ara) gelince → direkt tool çağır

ÖRNEKLER:
- "İstanbul Kadıköy'de KBB doktoru ara" → şehir=İstanbul, ilçe=Kadıköy, query=KBB doktoru → HEMEN tara
- "diş hekimi ara" → "Hangi şehirde?"
- "merhaba" → "Merhaba! Lead bulmak, audit veya teklif için buradayım."
- "ne yapabilirsin" → kısa özet, 1-2 cümle

CEVAP KURALLARI:
- Maks 15 kelime
- "tabii/anladım/elbette/harika" yok
- Tool çağrısından sonra 1 cümle: "Başlattım — İstanbul KBB doktorları taranıyor."

Sektör belirleme (query'den çıkar, sormadan):
doktor/KBB/diş/göz/cerrah/klinik/hastane → klinik | kadın doğum/jinekolog → kadin_dogum
güzellik/kuaför/berber/estetik → guzellik | tesisat/elektrikçi → ev_hizmetleri
halı yıkama → hali_temizlik | klima/beyaz eşya → klima_beyaz_esya | oto tamir/lastik → oto_servis
çilingir/kilit → cilingir | tadilat/boyacı → tadilat | nakliye → nakliyat
kreş/kurs/dershane → egitim | kafe/restoran → restoran | avukat → avukat | emlak → emlak"""

SCRAPE_TOOL = {
    "name": "trigger_scrape",
    "description": "Kullanıcı onayladığında lead taraması başlatır. query kullanıcının söylediği arama ifadesi (KBB doktoru / diş hekimi vb), sector ise playbook/filtreleme için.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Kullanıcının söylediği Türkçe arama ifadesi, örn: 'kulak burun boğaz doktoru', 'diş hekimi', 'estetik cerrahi'",
            },
            "sector": {
                "type": "string",
                "enum": [
                    "klinik", "avukat", "emlak", "guzellik", "egitim",
                    "ev_hizmetleri", "kadin_dogum", "restoran", "oto_servis",
                    "klima_beyaz_esya", "cilingir", "tadilat", "nakliyat", "hali_temizlik",
                ],
            },
            "city": {"type": "string"},
            "district": {"type": "string"},
            "limit": {"type": "integer", "default": 20},
        },
        "required": ["query", "sector", "city"],
    },
}


@router.get("/status")
async def voice_status():
    return {
        "openai": bool(settings.OPENAI_API_KEY),
        "claude": bool(settings.CLAUDE_API_KEY),
    }


def _get_openai_client():
    if not settings.OPENAI_API_KEY:
        return None
    try:
        from openai import AsyncOpenAI
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    except ImportError:
        return None


# ── STT ────────────────────────────────────────────────────────────────

@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    client = _get_openai_client()
    if client is None:
        return {"text": "", "error": "OPENAI_API_KEY tanımlı değil"}

    audio_bytes = await audio.read()
    filename = audio.filename or "audio.webm"

    try:
        result = await client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, io.BytesIO(audio_bytes), audio.content_type or "audio/webm"),
            language="tr",
        )
        return {"text": result.text.strip()}
    except Exception as e:
        return {"text": "", "error": str(e)}


# ── TTS ────────────────────────────────────────────────────────────────

class SpeakRequest(BaseModel):
    text: str
    voice: str = "nova"


@router.post("/speak")
async def speak(body: SpeakRequest):
    client = _get_openai_client()
    if client is None:
        return Response(status_code=503, content=b"", media_type="audio/mpeg")

    try:
        response = await client.audio.speech.create(
            model="tts-1",
            voice=body.voice,  # type: ignore[arg-type]
            input=body.text,
            response_format="mp3",
        )
        return Response(content=response.content, media_type="audio/mpeg")
    except Exception:
        return Response(status_code=502, content=b"", media_type="audio/mpeg")


# ── Chat ───────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str


class VoiceChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class ScrapeAction(BaseModel):
    type: str = "scrape"
    job_id: str
    sector: str
    city: str
    district: str = ""
    limit: int = 20


class VoiceChatResponse(BaseModel):
    reply: str
    action: ScrapeAction | None = None


# System + tools with cache_control — 5dk cache, %90 ucuz
_CACHED_SYSTEM = [{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]
_CACHED_TOOLS = [{**SCRAPE_TOOL, "cache_control": {"type": "ephemeral"}}]


@router.post("/chat", response_model=VoiceChatResponse)
async def voice_chat(
    body: VoiceChatRequest,
    db: AsyncSession = Depends(get_db),
    arq: ArqRedis = Depends(get_arq_pool),
):
    client = _get_claude_client()
    if client is None:
        return VoiceChatResponse(reply="Asistan kullanılamıyor.")

    trimmed = body.history[-10:]
    messages = [{"role": m.role, "content": m.content} for m in trimmed]
    messages.append({"role": "user", "content": body.message})

    try:
        response = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=400,
            temperature=0.4,
            system=_CACHED_SYSTEM,  # type: ignore[arg-type]
            tools=_CACHED_TOOLS,  # type: ignore[arg-type]
            messages=messages,
        )

        text_parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
        reply = "".join(text_parts).strip()
        tool_blocks = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
        action = None

        if tool_blocks:
            tool = tool_blocks[0]
            inp = tool.input  # type: ignore[attr-defined]
            sector = inp["sector"]
            city = inp["city"]
            district = inp.get("district", "") or ""
            query = (inp.get("query") or "").strip()
            limit = int(inp.get("limit", 20))

            job = await JobRepository(db).create(
                type="collect_leads",
                payload={"sector": sector, "city": city, "district": district, "limit": limit, "query": query},
            )
            await db.commit()
            await arq.enqueue_job("run_collect_job", sector, city, district, limit, str(job.id), query)

            # If Claude didn't provide text with the tool call, give a fixed short confirm
            if not reply:
                reply = f"Başlattım. {city} {query or sector} için {limit} lead."

            action = ScrapeAction(job_id=str(job.id), sector=sector, city=city, district=district, limit=limit)

    except Exception:
        return VoiceChatResponse(reply="Hata, tekrar dene.")

    return VoiceChatResponse(reply=reply, action=action)
