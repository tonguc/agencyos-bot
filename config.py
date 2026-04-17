import json
import logging
from pathlib import Path

from core.utils import validate_playbook

logger = logging.getLogger(__name__)

PLAYBOOKS_DIR = Path(__file__).parent / "playbooks"


def load_playbook(sektor: str) -> dict:
    path = PLAYBOOKS_DIR / f"{sektor}.json"
    if not path.exists():
        raise FileNotFoundError(f"Playbook bulunamadı: {sektor}")
    with open(path, encoding="utf-8") as f:
        pb = json.load(f)
    valid, errors = validate_playbook(pb)
    if not valid:
        raise ValueError(f"Playbook hatalı ({sektor}): {errors}")
    return pb


def list_playbooks() -> list[str]:
    if not PLAYBOOKS_DIR.exists():
        return []
    return sorted(p.stem for p in PLAYBOOKS_DIR.glob("*.json"))
