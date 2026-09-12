import logging
from collections import Counter

from config import settings

ICP_STRICT_MODE = settings.ICP_STRICT_MODE

logger = logging.getLogger(__name__)


def filter_leads(leads: list[dict], playbook: dict) -> dict:
    filtre = dict(playbook["icp_filtre"])

    if not ICP_STRICT_MODE:
        filtre["yorum_min"] = max(0, filtre.get("yorum_min", 0) - 3)
        filtre["yorum_max"] = filtre.get("yorum_max", 10_000) + 30
        logger.info("ICP genis mod aktif (STRICT_MODE=false) — puan_max playbook'taki degerde kalir")

    nitelikli: list[dict] = []
    elendi: list[dict] = []

    for lead in leads:
        gecti, neden = _check_single_lead(lead, filtre)
        isim = lead.get("isim") or "<isimsiz>"
        # Target profile is context, never grounds for dropping a prospect.
        if not gecti:
            note = f"Hedef profil notu: {neden}. Başvuru listesinde tutuldu."
            notes = lead.setdefault("qualification_notes", [])
            if note not in notes:
                notes.append(note)
        nitelikli.append(lead)

    toplam = len(leads)
    gecis = (len(nitelikli) / toplam * 100) if toplam else 0
    logger.info("ICP sonuc: %d/%d gecti (%.0f%%)", len(nitelikli), toplam, gecis)

    return {
        "nitelikli": nitelikli,
        "elendi": elendi,
        "istatistik": {
            "toplam": toplam,
            "gecen": len(nitelikli),
            "elenen": len(elendi),
            "gecis_orani": round(gecis, 1),
        },
    }


def _check_single_lead(lead: dict, filtre: dict) -> tuple[bool, str]:
    isim = (lead.get("isim") or "").lower()

    for kelime in filtre.get("eleme_kriterleri", []):
        if kelime and kelime.lower() in isim:
            return False, f"eleme: '{kelime}' ismi iceriyor"

    yorum = lead.get("yorum_sayisi") or 0
    yorum_min = filtre.get("yorum_min", 0)
    yorum_max = filtre.get("yorum_max", 10_000)
    if yorum < yorum_min:
        return False, f"yorum az ({yorum} < {yorum_min})"
    if yorum > yorum_max:
        return False, f"yorum cok ({yorum} > {yorum_max})"

    puan_max = filtre.get("puan_max")
    if puan_max is not None:
        puan = lead.get("puan") or 0
        if puan and puan > puan_max:
            return False, f"puan yuksek ({puan} > {puan_max})"

    kabul = filtre.get("site_durumu_kabul")
    if kabul:
        durum = lead.get("site_durumu") or "yok"
        if durum not in kabul:
            return False, f"site durumu '{durum}' kabul listesinde degil"

    return True, "nitelikli"


def get_filter_summary(result: dict) -> str:
    ist = result.get("istatistik", {})
    lines = [
        "ICP Filtre Sonucu",
        f"Toplam: {ist.get('toplam', 0)}",
        f"Gecen: {ist.get('gecen', 0)}",
        f"Elenen: {ist.get('elenen', 0)} (%{100 - ist.get('gecis_orani', 0):.0f})",
    ]

    nedenler: Counter = Counter()
    for e in result.get("elendi", []):
        neden = e.get("neden") or "bilinmiyor"
        anahtar = neden.split(":")[0].split("(")[0].strip()
        nedenler[anahtar] += 1

    if nedenler:
        lines.append("")
        lines.append("Eleme nedenleri:")
        for neden, sayi in nedenler.most_common():
            lines.append(f"- {neden}: {sayi}")

    return "\n".join(lines)
