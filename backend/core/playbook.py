"""Playbook loader — sector-specific configuration."""

import json
import logging
import os

from config import settings

logger = logging.getLogger(__name__)


def load_playbook(sector: str, fallback: str | None = None) -> dict:
    """Load and return a sector playbook JSON.

    If `fallback` verilirse, dosya yoksa o playbook'a düşer (loglar + fallback döner).
    `fallback=None` (default) eski davranış: ValueError.
    """
    path = os.path.join(settings.PLAYBOOKS_DIR, f"{sector}.json")
    if not os.path.exists(path):
        if fallback:
            logger.warning("Playbook bulunamadi: %s → fallback: %s", sector, fallback)
            return load_playbook(fallback)  # fallback dosyasi da yoksa ValueError atacak
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
    # Yeni sektörler
    "oto_servis",
    "klima_beyaz_esya",
    "cilingir",
    "tadilat",
    "nakliyat",
    "hali_temizlik",
]


def list_top_level_sectors() -> list[str]:
    """Return only the user-facing top-level sector codes."""
    return TOP_LEVEL_SECTORS


# Default subsector playbook used at collection time (before subsector detection).
# Audit/funnel stages re-detect the actual subsector from the lead data.
_DEFAULT_PLAYBOOK: dict[str, str] = {
    "klinik":          "clinic_general",
    "avukat":          "lawyer_litigation",
    "emlak":           "real_estate_local",
    "guzellik":        "beauty_routine",
    "egitim":          "education_course",
    "ev_hizmetleri":   "ev_hizmetleri_tesisat",
    "kadin_dogum":     "clinic_general",
    # Yeni sektörler
    "oto_servis":      "oto_servis",
    "klima_beyaz_esya": "klima_beyaz_esya",
    "cilingir":        "cilingir",
    "tadilat":         "tadilat",
    "nakliyat":        "nakliyat",
    "hali_temizlik":   "hali_temizlik",
    # Fallback aliases
    "genel":           "clinic_general",
    "general":         "clinic_general",
}

_FALLBACK_PLAYBOOK = "clinic_general"


def load_playbook_for_sector(sector: str) -> dict:
    """
    Load a playbook for a top-level sector.
    Falls back to clinic_general for unknown sectors.
    """
    resolved = _DEFAULT_PLAYBOOK.get(sector or "", _FALLBACK_PLAYBOOK)
    try:
        return load_playbook(resolved)
    except ValueError:
        logger.warning("Playbook bulunamadı: %s → fallback: %s", resolved, _FALLBACK_PLAYBOOK)
        return load_playbook(_FALLBACK_PLAYBOOK)
