"""
Bot handlers — all business logic delegated to FastAPI via bot.api_client.
No direct core/ or DB imports here.
"""

import io
import logging
import os

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

import bot.api_client as api
from bot.formatters import (
    format_audit,
    format_followup,
    format_lead_list,
    format_outreach,
    format_pipeline,
    format_scrape_result,
    format_teklif_summary,
    format_yardim,
)

logger = logging.getLogger(__name__)


# ── auth ───────────────────────────────────────────────────────────────

def _allowed_ids() -> set[int]:
    raw = os.getenv("ALLOWED_USER_IDS", "")
    return {int(p) for p in raw.split(",") if p.strip().isdigit()}


async def _guard(update: Update) -> bool:
    allowed = _allowed_ids()
    if not allowed:
        return True
    user = update.effective_user
    if user and user.id in allowed:
        return True
    await update.message.reply_text("Yetkisiz kullanici.")
    return False


async def _typing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    except Exception:
        pass


# ── /lead sektor sehir [ilce] [limit] ─────────────────────────────────

async def handle_lead(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "Kullanim: /lead <sektor> <sehir> [ilce] [limit=20]\n"
            "Ornek: /lead klinik Istanbul Kadikoy 25"
        )
        return

    sector, city = args[0], args[1]
    district = args[2] if len(args) >= 3 and not args[2].isdigit() else ""
    limit = int(args[-1]) if args[-1].isdigit() else 20

    await _typing(update, context)
    await update.message.reply_text(f"Tarama basliyor: {sector} / {city}...")

    try:
        job = await api.trigger_scrape(sector, city, district, limit)
        await update.message.reply_text("Kuyruga alindi, bekleniyor...")
        result = await api.poll_job(job["job_id"])
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return

    if result["status"] == "failed":
        await update.message.reply_text(f"Tarama basarisiz: {result.get('error_message', '?')}")
        return

    await update.message.reply_text(format_scrape_result(result.get("result") or {}))


# ── /liste [status] ────────────────────────────────────────────────────

async def handle_liste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    args = context.args or []
    status = args[0] if args else None
    await _typing(update, context)
    try:
        data = await api.list_leads(status=status, limit=10)
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return
    await update.message.reply_text(format_lead_list(data["items"], status))


# ── /audit <lead_id | toplu> ───────────────────────────────────────────

async def handle_audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    args = context.args or []
    if not args:
        await update.message.reply_text("Kullanim: /audit <lead_id | toplu>")
        return

    await _typing(update, context)

    if args[0].lower() == "toplu":
        data = await api.list_leads(status="Yeni", limit=50)
        leads = sorted(data["items"], key=lambda l: l.get("opportunity_score") or 0, reverse=True)[:5]
        if not leads:
            await update.message.reply_text("Yeni durumunda lead yok.")
            return
        await update.message.reply_text(f"{len(leads)} lead icin toplu audit basliyor...")
        for i, lead in enumerate(leads, 1):
            await update.message.reply_text(f"Audit {i}/{len(leads)}: {lead['name']}...")
            await _run_audit(update, lead["id"])
        return

    await _run_audit(update, args[0])


async def _run_audit(update: Update, lead_id: str):
    try:
        job = await api.trigger_audit(lead_id)
        result = await api.poll_job(job["job_id"])
    except Exception as e:
        await update.message.reply_text(f"Audit hatasi ({lead_id[:8]}): {e}")
        return

    if result["status"] == "failed":
        await update.message.reply_text(f"Audit basarisiz: {result.get('error_message', '?')}")
        return

    lead = await api.get_lead(lead_id)
    audit = await api.get_audit(lead_id)
    if lead and audit:
        await update.message.reply_text(format_audit(lead, audit))
    else:
        await update.message.reply_text(f"Audit tamamlandi: {lead_id[:8]}")


# ── /mesaj <lead_id> ───────────────────────────────────────────────────

async def handle_mesaj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    args = context.args or []
    if not args:
        await update.message.reply_text("Kullanim: /mesaj <lead_id>")
        return

    lead_id = args[0]
    await _typing(update, context)

    try:
        job = await api.trigger_outreach(lead_id)
        await update.message.reply_text("Mesajlar yaziliyor...")
        result = await api.poll_job(job["job_id"])
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return

    if result["status"] == "failed":
        await update.message.reply_text(f"Outreach basarisiz: {result.get('error_message', '?')}")
        return

    lead = await api.get_lead(lead_id)
    outreach = await api.get_outreach(lead_id)
    if lead and outreach:
        await update.message.reply_text(format_outreach(lead, outreach))
    else:
        await update.message.reply_text(f"Outreach tamamlandi: {lead_id[:8]}")


# ── /gonder <lead_id> <v1|v2|v3|v4> ───────────────────────────────────

async def handle_gonder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    args = context.args or []
    if len(args) < 2 or args[1] not in ("v1", "v2", "v3", "v4"):
        await update.message.reply_text("Kullanim: /gonder <lead_id> <v1|v2|v3|v4>")
        return

    lead_id, version = args[0], args[1]
    await _typing(update, context)

    outreach = await api.get_outreach(lead_id)
    if not outreach:
        await update.message.reply_text("Outreach bulunamadi. Once /mesaj calistir.")
        return

    try:
        await api.mark_sent(lead_id, outreach["id"], version)
        await update.message.reply_text(
            f"{version.upper()} gonderildi olarak kaydedildi.\n"
            f"3 gun sonra: /followup {lead_id}"
        )
    except Exception as e:
        await update.message.reply_text(f"Kaydedilemedi: {e}")


# ── /followup <lead_id> ────────────────────────────────────────────────

async def handle_followup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    args = context.args or []
    if not args:
        await update.message.reply_text("Kullanim: /followup <lead_id>")
        return

    lead_id = args[0]
    await _typing(update, context)

    try:
        text = await api.get_followup(lead_id)
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return

    await update.message.reply_text(format_followup(text))


# ── /teklif <lead_id> ──────────────────────────────────────────────────

async def handle_teklif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    args = context.args or []
    if not args:
        await update.message.reply_text("Kullanim: /teklif <lead_id>")
        return

    lead_id = args[0]
    await _typing(update, context)
    await update.message.reply_text("Teklif hazirlaniyor... (15-30 sn)")

    try:
        job = await api.trigger_proposal(lead_id)
        result = await api.poll_job(job["job_id"])
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return

    if result["status"] == "failed":
        await update.message.reply_text(f"Teklif basarisiz: {result.get('error_message', '?')}")
        return

    lead = await api.get_lead(lead_id)
    proposal = await api.get_proposal(lead_id)
    if not proposal:
        await update.message.reply_text("Teklif olusturuldu ama getirilemedi.")
        return

    caption = format_teklif_summary(lead or {}, proposal.get("content") or {})

    try:
        pdf_bytes = await api.download_pdf(proposal["id"])
        name = f"teklif-{(lead or {}).get('name', lead_id[:8])}.pdf"
        await update.message.reply_document(
            document=io.BytesIO(pdf_bytes),
            filename=name,
            caption=caption,
        )
    except Exception as e:
        logger.warning("PDF gonderilemedi: %s", e)
        await update.message.reply_text(caption + f"\n\nPDF indirilemedi: {e}")


# ── /durum ─────────────────────────────────────────────────────────────

async def handle_durum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    await _typing(update, context)
    try:
        counts = await api.pipeline_counts()
    except Exception as e:
        await update.message.reply_text(f"Hata: {e}")
        return
    await update.message.reply_text(format_pipeline(counts))


# ── /yardim ────────────────────────────────────────────────────────────

async def handle_yardim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return
    await update.message.reply_text(format_yardim())
