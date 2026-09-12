from core.sales_policy import SALES_POLICY, PROPOSAL_TERMS
from core import prompts
from core.proposal_generator import build_proposal_html


def test_policy_covers_all_customer_message_paths():
    for name in ("OUTREACH_PROMPT", "FOLLOWUP_PROMPT_DAY3", "FOLLOWUP_PROMPT_LAST", "INITIAL_MESSAGE_PROMPT", "REPLY_RESPONSE_PROMPT", "CLOSE_PROMPT"):
        assert getattr(prompts, name).startswith(SALES_POLICY)
        assert getattr(prompts, name).endswith(SALES_POLICY)


def test_proposal_pdf_exposes_unapproved_terms():
    html = build_proposal_html({"isim": "Test"}, {}, dict(PROPOSAL_TERMS), {})
    assert PROPOSAL_TERMS["teklif_durumu"] in html
    assert PROPOSAL_TERMS["teslim_suresi"] in html
    assert "Sıralama veya müşteri sayısı garantisi verilmez" in html
