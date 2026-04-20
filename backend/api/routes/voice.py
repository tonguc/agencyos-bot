from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from arq import ArqRedis

from config import settings
from core.utils import _get_claude_client
from database import get_db
from jobs.pool import get_arq_pool
from repositories.job import JobRepository

router = APIRouter(prefix="/voice", tags=["voice"])

SYSTEM_PROMPT = """Sen AgencyOS'un sesli asistanısın. Kullanıcıyla Türkçe, samimi ve kısa konuşursun.

AgencyOS özellikleri:
- Lead Topla: Google Maps'ten sektör + şehir bazlı işletme lead'i toplar
- Adaylar: Lead listesi ve fırsat skorları (0-100)
- Görevler: Tarama ve audit işleri
- Pipeline: Lead süreç takibi (Yeni → Kapandı)

Desteklenen sektörler:
klinik, avukat, emlak, guzellik, egitim, ev_hizmetleri, kadin_dogum, restoran, oto_servis, klima_beyaz_esya, cilingir, tadilat, nakliyat, hali_temizlik

Kullanıcı tarama yapmak istiyorsa:
1. Sektör ve şehri sor (eksikse)
2. İlçe ve limit sor (opsiyonel, default limit=20)
3. Kullanıcı onayladıktan sonra trigger_scrape aracını çağır

Kurallar:
- Cevaplar kısa olsun (1-3 cümle) — sesli okunacak
- Tarama başlatmadan önce mutlaka onay al
- Sektör adı Türkçe söylenirse doğru key'e çevir (örn: "güzellik" → "guzellik")
- Şehir adını büyük harfle yaz (örn: "istanbul" → "İstanbul")"""

SCRAPE_TOOL = {
    "name": "trigger_scrape",
    "description": "Kullanıcı onayladığında Google Maps lead taraması başlatır",
    "input_schema": {
        "type": "object",
        "properties": {
            "sector": {
                "type": "string",
                "enum": [
                    "klinik", "avukat", "emlak", "guzellik", "egitim",
                    "ev_hizmetleri", "kadin_dogum", "restoran", "oto_servis",
                    "klima_beyaz_esya", "cilingir", "tadilat", "nakliyat", "hali_temizlik",
                ],
                "description": "Sektör key'i",
            },
            "city": {
                "type": "string",
                "description": "Türkçe şehir adı, örn: İstanbul",
            },
            "district": {
                "type": "string",
                "description": "İlçe adı (opsiyonel, boş bırakılabilir)",
            },
            "limit": {
                "type": "integer",
                "description": "Kaç lead toplanacak, default 20",
                "default": 20,
            },
        },
        "required": ["sector", "city"],
    },
}


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


@router.post("/chat", response_model=VoiceChatResponse)
async def voice_chat(
    body: VoiceChatRequest,
    db: AsyncSession = Depends(get_db),
    arq: ArqRedis = Depends(get_arq_pool),
):
    client = _get_claude_client()
    if client is None:
        return VoiceChatResponse(reply="Asistan şu anda kullanılamıyor, API anahtarını kontrol et.")

    messages = [{"role": m.role, "content": m.content} for m in body.history]
    messages.append({"role": "user", "content": body.message})

    try:
        response = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=400,
            temperature=0.5,
            system=SYSTEM_PROMPT,
            tools=[SCRAPE_TOOL],
            messages=messages,
        )

        # Extract text reply
        text_parts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
        reply = "".join(text_parts).strip()

        # Check for tool use
        tool_blocks = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
        action = None

        if tool_blocks:
            tool = tool_blocks[0]
            inp = tool.input  # type: ignore[attr-defined]
            sector = inp["sector"]
            city = inp["city"]
            district = inp.get("district", "") or ""
            limit = int(inp.get("limit", 20))

            # Execute scrape job
            job = await JobRepository(db).create(
                type="collect_leads",
                payload={"sector": sector, "city": city, "district": district, "limit": limit},
            )
            await db.commit()
            await arq.enqueue_job("run_collect_job", sector, city, district, limit, str(job.id))

            # Second call: get Claude's confirmation message
            messages_with_result = messages + [
                {"role": "assistant", "content": response.content},  # type: ignore[list-item]
                {
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool.id,  # type: ignore[attr-defined]
                        "content": f"Tarama başlatıldı. Job ID: {job.id}. Sektör: {sector}, Şehir: {city}, Limit: {limit}",
                    }],
                },
            ]
            follow = await client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=200,
                temperature=0.5,
                system=SYSTEM_PROMPT,
                messages=messages_with_result,
            )
            follow_parts = [b.text for b in follow.content if getattr(b, "type", None) == "text"]
            reply = "".join(follow_parts).strip() or reply

            action = ScrapeAction(
                job_id=str(job.id),
                sector=sector,
                city=city,
                district=district,
                limit=limit,
            )

    except Exception:
        return VoiceChatResponse(reply="Bir hata oluştu, lütfen tekrar dene.")

    return VoiceChatResponse(reply=reply, action=action)
