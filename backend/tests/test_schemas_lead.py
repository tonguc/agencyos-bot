"""LeadUpdate schema Literal validation (P1-A)."""

import pytest
from pydantic import ValidationError

from schemas.lead import LeadUpdate


def test_valid_status_accepted():
    m = LeadUpdate(status="Yeni")
    assert m.status == "Yeni"

    m = LeadUpdate(status="Kapandi")
    assert m.status == "Kapandi"


def test_invalid_status_rejected():
    with pytest.raises(ValidationError):
        LeadUpdate(status="Mesaj Gönderiliyor")   # typo

    with pytest.raises(ValidationError):
        LeadUpdate(status="Soguk")  # migration 0003'te Arsiv olarak rename edildi

    with pytest.raises(ValidationError):
        LeadUpdate(status="")


def test_none_status_ok():
    m = LeadUpdate(status=None)
    assert m.status is None


def test_valid_priority():
    m = LeadUpdate(priority="yuksek")
    assert m.priority == "yuksek"


def test_invalid_priority_rejected():
    with pytest.raises(ValidationError):
        LeadUpdate(priority="HIGH")
