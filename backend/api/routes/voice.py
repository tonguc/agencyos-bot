import io
import logging

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from arq import ArqRedis

from config import settings
from core.utils import _get_claude_client
from database import get_db
from jobs.pool import get_arq_pool
from repositories.job import JobRepository

logger = logging.getLogger(__name__)

# OpenAI TTS hard limit (tts-1 model). Daha uzun input kesilir + uyari.
TTS_MAX_CHARS = 4096

router = APIRouter(prefix="/voice", tags=["voice"])

SYSTEM_PROMPT = """Sen AgencyOS'un sesli asistanısın. Türkçe konuş.

SOHBET KURALLARI:
- "merhaba/selam" → "Merhaba!" veya "Selam, nasılsın?"
- "nasılsın/naber/iyi misin" → "İyiyim, teşekkürler! Sen nasılsın?" — BAŞKA BİR ŞEY SÖYLEME
- "ne yaparsın/yapabilirsin" → "Lead bulur, audit yapar, teklif hazırlarım."
- "bulamadın mı / ne zaman biter / oldu mu" → "Jobs sayfasında takip edebilirsin."
- Sormadan görev tanımı anlatma. Her mesajı aramaya çevirme.

ARAMA İSTEKLERİ (ÖNEMLİ):
Sesli tarama şu an devre dışı. Kullanıcı "ara/tara/bak/listele/getir/çek"
fiillerinden biriyle sektör/şehir söylerse:
  → "Sesli tarama şu an kapalı. Yeni Tarama sayfasından başlatabilirsin."
Başka hiçbir şey söyleme. Tool ÇAĞIRMA.

CEVAP KURALLARI:
- Maks 15 kelime
- "tabii/anladım/elbette/harika" kullanma"""

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
        logger.exception("voice/transcribe failed | bytes=%d type=%s",
                         len(audio_bytes), audio.content_type)
        return {"text": "", "error": str(e)}


# ── TTS ────────────────────────────────────────────────────────────────

class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice: str = "nova"


@router.post("/speak")
async def speak(body: SpeakRequest):
    client = _get_openai_client()
    if client is None:
        return Response(status_code=503, content=b"", media_type="audio/mpeg")

    # OpenAI TTS 4096 char limit — uzun input 400 dondurur ve cost'u boşa harcar.
    text = body.text
    if len(text) > TTS_MAX_CHARS:
        logger.warning("voice/speak text truncated: %d -> %d chars",
                       len(text), TTS_MAX_CHARS)
        text = text[:TTS_MAX_CHARS]

    try:
        response = await client.audio.speech.create(
            model="tts-1",
            voice=body.voice,  # type: ignore[arg-type]
            input=text,
            response_format="mp3",
        )
        return Response(content=response.content, media_type="audio/mpeg")
    except Exception:
        logger.exception("voice/speak failed | chars=%d voice=%s",
                         len(text), body.voice)
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
            # Tool use kapali (asagida tool_blocks override ediliyor) — text reply
            # zaten sistem prompt'ta max 15 kelime, 400 gereksiz buyuktu.
            max_tokens=200,
            temperature=0.4,
            system=_CACHED_SYSTEM,  # type: ignore[arg-type]
            tools=_CACHED_TOOLS,  # type: ignore[arg-type]
            messages=messages,
            timeout=30.0,
        )

        text_parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
        reply = "".join(text_parts).strip()
        tool_blocks = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
        action = None

        if tool_blocks:
            # Scrape via voice is disabled — unstable, wastes Apify credits.
            # User should trigger scrapes manually from Yeni Tarama page.
            reply = "Şu an sesli tarama devre dışı. Yeni Tarama sayfasından başlatabilirsin."
            action = None

    except Exception:
        return VoiceChatResponse(reply="Hata, tekrar dene.")

    return VoiceChatResponse(reply=reply, action=action)
