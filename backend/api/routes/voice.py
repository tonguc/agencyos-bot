from fastapi import APIRouter
from pydantic import BaseModel

from core.utils import _get_claude_client
from config import settings

router = APIRouter(prefix="/voice", tags=["voice"])

SYSTEM_PROMPT = """Sen AgencyOS'un sesli asistanısın. AgencyOS, Türkiye pazarında faaliyet gösteren yerel işletmelere yönelik lead bulma ve dijital ajans hizmetleri sunan bir sistemdir.

Sistem özellikleri:
- Lead Topla (Scrape): Google Maps'ten sektör + şehir bazlı işletme lead'i toplar
- Adaylar (Leads): Toplanan lead'leri listeler, filtreler, puanlar (0-100 fırsat skoru)
- Görevler (Jobs): Tarama ve audit işlerinin durumunu gösterir
- Pipeline: Lead'lerin Yeni → Audit → Mesaj → Kapandı sürecini takip eder
- Firma Ara (Search): AI destekli firma arama
- Ayarlar: Sistem konfigürasyonu

Fırsat skoru:
- 65+ = Yüksek (sıcak lead, hemen mesaj at)
- 45-64 = Orta (audit başlat)
- 45 altı = Düşük (gözden geçir)

Desteklenen sektörler: Klinik, Avukat, Emlak, Güzellik, Eğitim, Tesisat, Kadın Doğum, Restoran, Oto Servis, Klima/Beyaz Eşya, Çilingir, Tadilat, Nakliyat, Halı & Temizlik.

Kurallar:
- Cevaplarını kısa ve net tut (1-3 cümle ideal, sesli okunacak)
- Türkçe konuş, samimi ama profesyonel ol
- Teknik jargon kullanma, kullanıcıya yol göster
- Sistemin hangi sayfasına gideceğini söyle gerektiğinde
- Sayısal veri yoksa tahminde bulunma, "kontrol et" de"""


class ChatMessage(BaseModel):
    role: str
    content: str


class VoiceChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class VoiceChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=VoiceChatResponse)
async def voice_chat(body: VoiceChatRequest):
    client = _get_claude_client()
    if client is None:
        return VoiceChatResponse(reply="Asistan şu anda kullanılamıyor, API anahtarını kontrol et.")

    messages = [{"role": m.role, "content": m.content} for m in body.history]
    messages.append({"role": "user", "content": body.message})

    try:
        msg = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=300,
            temperature=0.5,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
        reply = "".join(parts).strip()
    except Exception:
        reply = "Bir hata oluştu, lütfen tekrar dene."

    return VoiceChatResponse(reply=reply)
