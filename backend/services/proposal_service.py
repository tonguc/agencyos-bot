"""
Proposal Service — orchestration only.
No FastAPI, ARQ, or Telegram imports.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core.playbook import load_playbook_for_sector
from core.proposal_generator import generate_proposal
from models.activity_log import ActivityEvent
from models.proposal import Proposal
from repositories.audit import AuditRepository
from repositories.lead import LeadRepository
from repositories.proposal import ProposalRepository
from services.activity import log_event
from services.lead_service import lead_to_core_dict

logger = logging.getLogger(__name__)


async def generate_proposal_for_lead(lead_id: uuid.UUID, db: AsyncSession) -> Proposal:
    """Generate PDF proposal for a lead. Returns saved Proposal ORM instance."""
    lead = await LeadRepository(db).get(lead_id)
    if not lead:
        raise ValueError(f"Lead bulunamadi: {lead_id}")

    playbook = load_playbook_for_sector(lead.sector or "klinik")
    lead_dict = lead_to_core_dict(lead)

    audit = await AuditRepository(db).get_latest_for_lead(lead_id)
    audit_dict = audit.result if audit else {}

    pdf_path, content = await generate_proposal(lead_dict, audit_dict, playbook)

    proposal = await ProposalRepository(db).create(
        lead_id=lead_id,
        audit_id=audit.id if audit else None,
        content=content,
        pdf_path=pdf_path,
    )

    await LeadRepository(db).update(lead, status="Teklif")
    await log_event(db, event=ActivityEvent.PROPOSAL_GENERATED,
                    lead_id=lead_id, data={"proposal_id": str(proposal.id),
                                           "pdf_path": pdf_path})
    logger.info("Proposal uretildi: lead=%s pdf=%s", str(lead_id)[:8], pdf_path)
    return proposal
