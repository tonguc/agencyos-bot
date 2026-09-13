"""Conservative sales routing from recorded institution signals, not legal status verification."""
import re
import unicodedata


def public_health_sales_note(lead: dict) -> str | None:
    def clean(value):
        text = unicodedata.normalize("NFKD", str(value or "").casefold())
        return "".join(c for c in text if not unicodedata.combining(c)).replace("ı", "i")

    # Only current record fields: do not scan scraped biographies or past jobs.
    text = " | ".join(clean(lead.get(k)) for k in ("isim", "adres", "kategori"))
    identity = " ".join(clean(lead.get(k)) for k in ("isim", "kategori"))
    if lead.get("sektor") not in {"klinik", "kadin_dogum"} and not re.search(r"\b(dr|doktor|doctor|hekim|hastanesi|hospital|physician)\b", identity):
        return None
    patterns = (
        r"\bdevlet hastane(?:si|sinde|sinin)?\b",
        r"\bsehir hastane(?:si|sinde|sinin)?\b",
        r"\begitim (?:ve )?arastirma hastane(?:si|sinde|sinin)?\b",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            # A nearby landmark or street name does not establish employment.
            tail = text[match.end():].lstrip(" '’")
            if re.match(r"(?:caddesi|cad\b|cd\b|sokak|sokagi|sk\b|karsisi|yani|yakininda)", tail):
                continue
            return (
                "Aktif satış dışında: kayıtta kamu hastanesi bağlantısı görünüyor. "
                "Özel muayenehaneye hasta edinme teklifi için uygun kabul edilmedi. "
                "Bu bir görev statüsü doğrulaması değildir; eski veya çelişkili kayıtta güncel kurum doğrulanmalı. "
                "Eğitim ve araştırma hastanesi adı otomatik istisna oluşturmaz."
            )
    return None
