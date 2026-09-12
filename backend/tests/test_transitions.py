"""Lead pipeline status transition guard — pure (DB-free) testler."""

import pytest

from services.lead_service import is_allowed_transition, ALLOWED_TRANSITIONS


def test_forward_transitions_allowed():
    assert is_allowed_transition("Yeni", "Audit")
    assert is_allowed_transition("Audit", "Mesaj")
    assert is_allowed_transition("Mesaj", "Cevap")
    assert is_allowed_transition("Cevap", "Teklif")
    assert is_allowed_transition("Teklif", "Kapandi")


def test_idempotent_self_transition_allowed():
    for s in ALLOWED_TRANSITIONS:
        assert is_allowed_transition(s, s)


def test_any_stage_to_arsiv_allowed():
    for s in ("Yeni", "Audit", "Mesaj", "Cevap", "Demo", "Teklif", "Kapandi"):
        assert is_allowed_transition(s, "Arsiv")


def test_closed_does_not_reopen():
    # Satisin bitmis oldugu "Kapandi" geri donemez
    assert not is_allowed_transition("Kapandi", "Mesaj")
    assert not is_allowed_transition("Kapandi", "Yeni")
    assert not is_allowed_transition("Kapandi", "Teklif")


def test_arsiv_is_terminal_except_self():
    for target in ("Yeni", "Audit", "Mesaj", "Cevap", "Demo", "Teklif", "Kapandi"):
        assert not is_allowed_transition("Arsiv", target)
    assert is_allowed_transition("Arsiv", "Arsiv")


def test_skip_stages_blocked():
    # Funnel atlamak yok: Yeni dogrudan Mesaj'a gidemez (once Audit lazim)
    assert not is_allowed_transition("Yeni", "Mesaj")
    assert not is_allowed_transition("Yeni", "Teklif")
    assert not is_allowed_transition("Audit", "Teklif")


def test_unknown_current_status_rejected():
    # Eski / bozulmus DB kayitlari icin defansif: bilinmeyen current -> transition yok
    assert not is_allowed_transition("Soguk", "Yeni")
    assert not is_allowed_transition("", "Yeni")
    assert not is_allowed_transition("RandomTypo", "Audit")


def test_unknown_new_status_rejected():
    assert not is_allowed_transition("Yeni", "Mesaj Gonderiliyor")
    assert not is_allowed_transition("Yeni", "")
