import os
import logging
from datetime import datetime, timezone
from collections import Counter

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from config import load_playbook
from core.lead_collector import collect_google_maps
from core.icp_filter import filter_leads, get_filter_summary
from core.opportunity_scorer import score_opportunity
from core.audit_generator import generate_audit
from core.hook_engine import select_and_generate_hook
from core.outreach_writer import write_outreach, write_followup
from core.proposal_generator import generate_proposal
from crm.notion_client import (
    create_lead,
    update_lead,
    get_lead,
    get_leads_by_status,
    get_pipeline_summary,
)
from bot.formatters import (
    format_lead_collect_summary,
    format_icp_summary,
    format_audit,
    format_outreach,
    format_pipeline,
    format_yardim,
    format_teklif_summary,
)

logger = logging.getLogger(__name__)


def _allowed_ids() -> set[int]:
    raw = os.getenv("ALLOWED_USER_IDS", "")
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


def _authorized(update: Update) -> bool:
    allowed = _allowed_ids()
    if not allowed:
        return True
    user = update.effective_user
    return bool(user and user.id in allowed)


async def _guard(update: Update) -> bool:
    if not _authorized(update):
        await update.message.reply_text("Yetkisiz kullanici.")
        logger.warning("Yetkisiz kullanici: %s", update.effective_user.id if update.effective_user else "?")
        return False
    return True


async def _typing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action=ChatAction.TYPING
        )
    except Exception:
        pass


def _synthetic_audit(lead: dict) -> dict:
    """Audit yoksa lead alanlarindan minimal bir audit stub uretir."""
    isim = lead.get("isim") or "isletme"
    website = lead.get("website")
    yorum = lead.get("yorum_sayisi") or 0
    puan = lead.get("puan") or 0
    telefon = lead.get("telefon")

    eksikler: list[str] = []
    if not website:
        eksikler.append("web sitesi yok")
    if yorum and yorum < 10:
        eksikler.append(f"yorum sayisi dusuk ({yorum})")
    if puan and puan < 4.0:
        eksikler.append(f"Google puani dusuk ({puan})")
    if not telefon:
        eksikler.append("Maps'te telefon linki yok")

    bulgu = " + ".join(eksikler) if eksikler else "dijital varlik zayif gorunuyor"
    en_acitan = (
        f"{isim} icin dijital temas noktalarinda belirgin eksikler var; "
        f"arama yapanlarin onemli bir kismi size ulasmadan rakibe gidiyor olabilir."
    )

    return {
        "killer_insight": {"bulgu": bulgu, "etki": "potansiyel musteri kaybi", "rakam": ""},
        "ux_hatalar": [],
        "seo_aciklar": [],
        "reklam_firsati": {"kanal": "", "aciklama": "", "rakip_durum": "yok"},
        "genel_skor": 40,
        "en_acitan_nokta": en_acitan,
        "_synthetic": True,
    }


async def handle_lead(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "Kullanim: /lead <sektor> <sehir> [ilce] [limit]\nOrnek: /lead klinik Istanbul Kadikoy 25"
        )
        return

    sektor, sehir = args[0], args[1]
    ilce = args[2] if len(args) >= 3 and not args[2].isdigit() else ""
    limit_arg = args[-1]
    limit = int(limit_arg) if limit_arg.isdigit() else 20

    try:
        playbook = load_playbook(sektor)
    except (FileNotFoundError, ValueError) as e:
        await update.message.reply_text(f"Playbook hatasi: {e}")
        return

    await _typing(update, context)
    await update.message.reply_text("Araniyor... (10-20 sn surebilir)")

    raw = await collect_google_maps(sektor, sehir, ilce, limit=limit)
    if not raw:
        await update.message.reply_text(
            "Lead bulunamadi veya Apify hatasi. Log'a bak (agencyos.log)."
        )
        return

    icp = filter_leads(raw, playbook)
    nitelikli = icp["nitelikli"]

    if not nitelikli:
        await update.message.reply_text(
            "ICP filtresinden gecen lead yok.\n\n" + get_filter_summary(icp)
        )
        return

    dagilim = Counter()
    kaydedilen = 0
    for lead in nitelikli:
        skor = score_opportunity(lead)
        dagilim[skor["oncelik"]] += 1
        page_id = await create_lead(lead, skor, sektor)
        if page_id:
            lead["page_id"] = page_id
            kaydedilen += 1

    en_sik = ""
    if icp["elendi"]:
        reasons = Counter(
            (e.get("neden") or "").split(":")[0].split("(")[0].strip()
            for e in icp["elendi"]
        )
        en_sik = reasons.most_common(1)[0][0]

    msg = format_lead_collect_summary(
        stats=icp["istatistik"],
        skor_dagilim={
            "yuksek": dagilim.get("yuksek", 0),
            "orta": dagilim.get("orta", 0),
            "dusuk": dagilim.get("dusuk", 0),
        },
        elendi_ornek=en_sik,
    )
    await update.message.reply_text(msg)


async def _audit_one(update: Update, context: ContextTypes.DEFAULT_TYPE, page_id: str) -> dict | None:
    lead = await get_lead(page_id)
    if not lead:
        await update.message.reply_text(f"Lead bulunamadi: {page_id}")
        return None
    sektor = lead.get("sektor") or "klinik"
    try:
        playbook = load_playbook(sektor)
    except (FileNotFoundError, ValueError) as e:
        await update.message.reply_text(f"Playbook hatasi: {e}")
        return None

    audit = await generate_audit(lead, playbook)
    hook = await select_and_generate_hook(lead, audit, playbook)

    import json as _json
    audit_json = _json.dumps(audit, ensure_ascii=False)
    logger.info(
        "Audit Notion'a yazilacak: %s | audit_len=%d char | uyari=%d",
        lead.get("isim"), len(audit_json), len(audit.get("_validation_warnings") or []),
    )
    ok = await update_lead(
        page_id,
        {
            "durum": "Audit",
            "audit_ozeti": audit,
            "hook_tipi": hook["tip"],
            "notlar": hook["hook"],
        },
    )
    if not ok:
        await update.message.reply_text(
            f"⚠ Notion'a yazilamadi (log'a bak). Lead: {lead.get('isim')}"
        )
    await update.message.reply_text(format_audit(lead, audit, hook))
    return {"lead": lead, "audit": audit, "hook": hook}


async def handle_audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    args = context.args or []
    if not args:
        await update.message.reply_text("Kullanim: /audit <lead_id | toplu>")
        return

    await _typing(update, context)

    if args[0].lower() == "toplu":
        yeni = await get_leads_by_status("Yeni", limit=50)
        yeni.sort(key=lambda l: l.get("firsat_skoru", 0), reverse=True)
        batch = yeni[:5]
        if not batch:
            await update.message.reply_text("Durum=Yeni olan lead yok.")
            return
        for i, lead in enumerate(batch, start=1):
            await update.message.reply_text(f"Audit {i}/{len(batch)} baslatiliyor...")
            await _audit_one(update, context, lead["page_id"])
        await update.message.reply_text(f"Toplu audit tamamlandi: {len(batch)} lead.")
        return

    await _audit_one(update, context, args[0])


async def handle_mesaj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    args = context.args or []
    if not args:
        await update.message.reply_text("Kullanim: /mesaj <lead_id>")
        return

    await _typing(update, context)
    page_id = args[0]
    lead = await get_lead(page_id)
    if not lead:
        await update.message.reply_text(f"Lead bulunamadi: {page_id}")
        return

    try:
        playbook = load_playbook(lead.get("sektor") or "klinik")
    except (FileNotFoundError, ValueError) as e:
        await update.message.reply_text(f"Playbook hatasi: {e}")
        return

    import json as _json
    raw = lead.get("audit_ozeti") or ""
    audit: dict = {}
    try:
        if raw:
            audit = _json.loads(raw)
    except _json.JSONDecodeError:
        logger.warning(
            "Mesaj: audit_ozeti bozuk JSON (%d char) — sentetik audit kullanilacak",
            len(raw),
        )

    stale = (audit.get("killer_insight") or {}).get("bulgu") in ("", "Analiz yapilamadi")
    synthetic = False
    if not audit or stale:
        audit = _synthetic_audit(lead)
        synthetic = True
        logger.info("Synthetic audit: %s (Notion'da audit yok)", lead.get("isim"))

    hook_tip_saved = lead.get("hook_tipi")
    hook_text_saved = lead.get("notlar")
    if synthetic or not hook_tip_saved or not hook_text_saved:
        hook = await select_and_generate_hook(lead, audit, playbook)
    else:
        hook = {"tip": hook_tip_saved, "hook": hook_text_saved}

    msgs = await write_outreach(lead, audit, hook, playbook)

    prefix = "ℹ Not: Audit kaydi yok, lead bilgisinden uretildi.\n\n" if synthetic else ""
    await update.message.reply_text(prefix + format_outreach(lead, hook["tip"], msgs))


async def handle_gonder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    args = context.args or []
    if len(args) < 2 or args[1] not in ("v1", "v2", "v3", "v4"):
        await update.message.reply_text("Kullanim: /gonder <lead_id> <v1|v2|v3|v4>")
        return

    page_id, versiyon = args[0], args[1]
    await _typing(update, context)

    ok = await update_lead(
        page_id,
        {
            "durum": "Mesaj",
            "mesaj_versiyonu": versiyon,
            "gonderilen_mesaj": f"[{versiyon}] gonderildi @ {datetime.now(timezone.utc).isoformat()}",
        },
    )
    if ok:
        await update.message.reply_text(
            f"Kaydedildi. 3 gun sonra: /followup {page_id}"
        )
    else:
        await update.message.reply_text("Kaydedilemedi — log'a bak.")


async def handle_followup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    args = context.args or []
    if not args:
        await update.message.reply_text("Kullanim: /followup <lead_id>")
        return

    await _typing(update, context)
    page_id = args[0]
    lead = await get_lead(page_id)
    if not lead:
        await update.message.reply_text(f"Lead bulunamadi: {page_id}")
        return

    try:
        playbook = load_playbook(lead.get("sektor") or "klinik")
    except (FileNotFoundError, ValueError) as e:
        await update.message.reply_text(f"Playbook hatasi: {e}")
        return

    ilk_temas = lead.get("ilk_temas")
    gun = 3
    if ilk_temas:
        try:
            dt = datetime.fromisoformat(ilk_temas)
            gun = max(1, (datetime.utcnow().date() - dt.date()).days)
        except ValueError:
            pass

    mesaj = await write_followup(lead, gun, lead.get("gonderilen_mesaj") or "", playbook)
    await update_lead(page_id, {"notlar": f"[followup gun={gun}] {mesaj}"})
    await update.message.reply_text(f"Followup (gun {gun}):\n\n{mesaj}")


async def handle_teklif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    args = context.args or []
    if not args:
        await update.message.reply_text("Kullanim: /teklif <lead_id>")
        return

    page_id = args[0]
    await _typing(update, context)
    await update.message.reply_text("Teklif hazirlaniyor... (15-30 sn surebilir)")

    lead = await get_lead(page_id)
    if not lead:
        await update.message.reply_text(f"Lead bulunamadi: {page_id}")
        return

    try:
        playbook = load_playbook(lead.get("sektor") or "klinik")
    except (FileNotFoundError, ValueError) as e:
        await update.message.reply_text(f"Playbook hatasi: {e}")
        return

    import json as _json4
    audit: dict = {}
    raw = lead.get("audit_ozeti") or ""
    try:
        if raw:
            audit = _json4.loads(raw)
    except _json4.JSONDecodeError:
        pass
    if not audit or not audit.get("killer_insight", {}).get("bulgu"):
        audit = _synthetic_audit(lead)

    try:
        pdf_path, content = await generate_proposal(lead, audit, playbook)
    except Exception as e:
        logger.exception("Teklif PDF hatasi: %s", e)
        await update.message.reply_text(f"PDF uretme hatasi: {e}")
        return

    await update_lead(page_id, {"durum": "Teklif"})

    import os as _os
    try:
        with open(pdf_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=_os.path.basename(pdf_path),
                caption=format_teklif_summary(lead, content),
            )
    finally:
        try:
            _os.remove(pdf_path)
            _os.rmdir(_os.path.dirname(pdf_path))
        except Exception:
            pass


async def handle_durum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    await _typing(update, context)
    counts = await get_pipeline_summary()
    await update.message.reply_text(format_pipeline(counts))


async def handle_yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    await update.message.reply_text(format_yardim())
