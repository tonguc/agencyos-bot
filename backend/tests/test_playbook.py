"""Playbook loader fallback davranisi (P1-6 / patch 10)."""

import pytest

from core.playbook import load_playbook


def test_load_valid_playbook():
    pb = load_playbook("clinic_general")
    assert isinstance(pb, dict)
    assert "sektor" in pb or "display_name" in pb


def test_missing_playbook_raises_without_fallback():
    with pytest.raises(ValueError):
        load_playbook("nonexistent_sector_xyz_123")


def test_missing_playbook_with_fallback_returns_fallback():
    pb = load_playbook("nonexistent_sector_xyz_123", fallback="clinic_general")
    assert isinstance(pb, dict)


def test_fallback_itself_missing_still_raises():
    # Hem hedef hem fallback yoksa exception atmali
    with pytest.raises(ValueError):
        load_playbook("nonexistent_a", fallback="nonexistent_b")
