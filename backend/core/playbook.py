"""Playbook loader — sector-specific configuration."""

import json
import logging
import os

from config import settings

logger = logging.getLogger(__name__)


def load_playbook(sector: str) -> dict:
    """Load and return a sector playbook JSON. Raises ValueError on missing/invalid."""
    path = os.path.join(settings.PLAYBOOKS_DIR, f"{sector}.json")
    if not os.path.exists(path):
        raise ValueError(f"Playbook bulunamadi: {path}")
    with open(path, encoding="utf-8") as f:
        playbook = json.load(f)
    return playbook


def list_playbooks() -> list[str]:
    """Return available sector names (all, including subsectors)."""
    d = settings.PLAYBOOKS_DIR
    if not os.path.isdir(d):
        return []
    return [f[:-5] for f in os.listdir(d) if f.endswith(".json")]


# Canonical top-level sectors shown in the UI dropdown.
# Order matters — displayed as-is.
TOP_LEVEL_SECTORS = [
    "klinik",
    "avukat",
    "emlak",
    "guzellik",
    "egitim",
    "ev_hizmetleri",
    "kadin_dogum",
]


def list_top_level_sectors() -> list[str]:
    """Return only the user-facing top-level sector codes."""
    return TOP_LEVEL_SECTORS
