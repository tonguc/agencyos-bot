from core.sales_policy import SALES_POLICY, PROPOSAL_TERMS
from core import prompts
from core.proposal_generator import build_proposal_html
from core.proposal_generator import generate_proposal_content
from core.outreach_writer import write_outreach
import pytest


def test_policy_covers_all_customer_message_paths():
    for name in ("OUTREACH_PROMPT", "FOLLOWUP_PROMPT_DAY3", "FOLLOWUP_PROMPT_LAST", "INITIAL_MESSAGE_PROMPT", "REPLY_RESPONSE_PROMPT", "CLOSE_PROMPT"):
        assert getattr(prompts, name).startswith(SALES_POLICY)
        assert getattr(prompts, name).endswith(SALES_POLICY)


def test_proposal_pdf_exposes_unapproved_terms():
    html = build_proposal_html({"isim": "Test"}, {}, dict(PROPOSAL_TERMS), {})
    assert PROPOSAL_TERMS["teklif_durumu"] in html
    assert PROPOSAL_TERMS["teslim_suresi"] in html
    assert "Sıralama veya müşteri sayısı garantisi verilmez" in html


@pytest.mark.asyncio
async def test_unknown_site_does_not_reuse_unsupported_audit_claims():
    audit = {"killer_insight": {"bulgu": "%70 hasta kaybı; puanın yarısı boşa gidiyor"}}
    proposal = await generate_proposal_content({"isim": "Örnek"}, audit, {})
    messages = await write_outreach({}, audit, {}, {})
    assert "%70" not in str(proposal) + str(messages)
    assert "yarısı" not in str(proposal) + str(messages)
    assert messages["onerilen"] == "v1"
    assert "yapay zekâ" in proposal["cozum"]
