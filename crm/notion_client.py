import os
import json
import asyncio
import logging
from datetime import datetime

from notion_client import Client

logger = logging.getLogger(__name__)

_client: Client | None = None

STATUS_VALUES = ["Yeni", "Audit", "Mesaj", "Cevap", "Demo", "Teklif", "Kapandi", "Soguk"]


def _get_client() -> Client | None:
    global _client
    if _client is not None:
        return _client
    key = os.getenv("NOTION_API_KEY")
    if not key:
        logger.error("NOTION_API_KEY .env'de tanimli degil")
        return None
    _client = Client(auth=key)
    return _client


def _db_id() -> str | None:
    """NOTION_DATABASE_ID artık data_source_id değerini tutuyor (yeni Notion API)."""
    return os.getenv("NOTION_DATABASE_ID")


def _title(text: str | None) -> list[dict]:
    return [{"type": "text", "text": {"content": (text or "")[:2000]}}]


NOTION_BLOCK_MAX = 2000
NOTION_RICHTEXT_MAX_BLOCKS = 10


def _rich(text: str | None) -> list[dict]:
    if not text:
        return [{"type": "text", "text": {"content": ""}}]
    total_cap = NOTION_BLOCK_MAX * NOTION_RICHTEXT_MAX_BLOCKS
    if len(text) > total_cap:
        text = text[: total_cap - 3] + "..."
    return [
        {"type": "text", "text": {"content": text[i : i + NOTION_BLOCK_MAX]}}
        for i in range(0, len(text), NOTION_BLOCK_MAX)
    ]


async def create_lead(lead: dict, skor: dict, sektor: str) -> str | None:
    client = _get_client()
    db = _db_id()
    if not client or not db:
        logger.warning("Notion yok — mock page_id donduruluyor")
        return f"mock_{abs(hash(lead.get('isim'))) % 10_000_000:07d}"

    bugun = datetime.utcnow().date().isoformat()
    props = {
        "Sirket": {"title": _title(lead.get("isim"))},
        "Sektor": {"select": {"name": sektor}},
        "Durum": {"select": {"name": "Yeni"}},
        "Firsat Skoru": {"number": int(skor.get("skor", 0))},
        "Kaynak": {"select": {"name": "Google Maps"}},
        "Ilk Temas": {"date": {"start": bugun}},
        "Son Aktivite": {"date": {"start": bugun}},
    }
    if lead.get("website"):
        props["Web Sitesi"] = {"url": lead["website"]}
    if lead.get("telefon"):
        props["Telefon"] = {"phone_number": lead["telefon"]}
    if skor.get("en_buyuk_acik"):
        props["Notlar"] = {"rich_text": _rich(skor["en_buyuk_acik"])}

    try:
        page = await asyncio.to_thread(
            client.pages.create,
            parent={"data_source_id": db},
            properties=props,
        )
        page_id = page["id"]
        logger.info("Notion'a kaydedildi: %s | %s", lead.get("isim"), page_id[:8])
        return page_id
    except Exception as e:
        logger.exception("Notion create_lead hatasi: %s", e)
        return None


async def update_lead(page_id: str, updates: dict) -> bool:
    client = _get_client()
    if not client:
        logger.warning("Notion yok — update_lead atlandi")
        return False

    props: dict = {}
    mapping = {
        "durum": ("Durum", "select"),
        "firsat_skoru": ("Firsat Skoru", "number"),
        "audit_ozeti": ("Audit Ozeti", "rich_text"),
        "hook_tipi": ("Hook Tipi", "select"),
        "gonderilen_mesaj": ("Gonderilen Mesaj", "rich_text"),
        "mesaj_versiyonu": ("Mesaj Versiyonu", "select"),
        "notlar": ("Notlar", "rich_text"),
        "cevap_geldi": ("Cevap Geldi Mi", "checkbox"),
        "cevap_tarihi": ("Cevap Tarihi", "date"),
        "gorusme_oldu": ("Gorusme Oldu Mu", "checkbox"),
        "kapandi": ("Kapandi Mi", "checkbox"),
        "red_nedeni": ("Red Nedeni", "select"),
    }
    for key, value in updates.items():
        if key not in mapping or value is None:
            continue
        name, typ = mapping[key]
        if typ == "select":
            props[name] = {"select": {"name": str(value)}}
        elif typ == "number":
            props[name] = {"number": value}
        elif typ == "rich_text":
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            props[name] = {"rich_text": _rich(value)}
        elif typ == "checkbox":
            props[name] = {"checkbox": bool(value)}
        elif typ == "date":
            props[name] = {"date": {"start": value}}

    props["Son Aktivite"] = {"date": {"start": datetime.utcnow().date().isoformat()}}

    try:
        await asyncio.to_thread(client.pages.update, page_id=page_id, properties=props)
        logger.info("Notion guncellendi: %s | %s", page_id[:8], list(updates.keys()))
        return True
    except Exception as e:
        logger.exception("Notion update_lead hatasi: %s", e)
        return False


async def get_lead(page_id: str) -> dict | None:
    client = _get_client()
    if not client:
        return None
    try:
        page = await asyncio.to_thread(client.pages.retrieve, page_id=page_id)
        return _parse_page(page)
    except Exception as e:
        logger.exception("Notion get_lead hatasi: %s", e)
        return None


async def get_leads_by_status(status: str, limit: int = 50) -> list[dict]:
    client = _get_client()
    db = _db_id()
    if not client or not db:
        return []
    try:
        result = await asyncio.to_thread(
            client.data_sources.query,
            data_source_id=db,
            filter={"property": "Durum", "select": {"equals": status}},
            page_size=min(limit, 100),
        )
        return [_parse_page(p) for p in result.get("results", [])]
    except Exception as e:
        logger.exception("Notion query hatasi: %s", e)
        return []


async def get_pipeline_summary() -> dict:
    client = _get_client()
    db = _db_id()
    if not client or not db:
        return {s: 0 for s in STATUS_VALUES}
    counts: dict[str, int] = {s: 0 for s in STATUS_VALUES}
    try:
        cursor = None
        while True:
            kwargs = {"data_source_id": db, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor
            res = await asyncio.to_thread(client.data_sources.query, **kwargs)
            for p in res.get("results", []):
                sel = p["properties"].get("Durum", {}).get("select")
                name = sel["name"] if sel else None
                if name in counts:
                    counts[name] += 1
            if not res.get("has_more"):
                break
            cursor = res.get("next_cursor")
    except Exception as e:
        logger.exception("Pipeline summary hatasi: %s", e)
    return counts


def _parse_page(page: dict) -> dict:
    props = page.get("properties", {})

    def _get_title(p):
        arr = p.get("title", [])
        return arr[0]["plain_text"] if arr else ""

    def _get_rich(p):
        arr = p.get("rich_text", [])
        return "".join(x.get("plain_text", "") for x in arr)

    def _get_select(p):
        s = p.get("select")
        return s["name"] if s else None

    return {
        "page_id": page.get("id"),
        "isim": _get_title(props.get("Sirket", {})),
        "sektor": _get_select(props.get("Sektor", {})),
        "durum": _get_select(props.get("Durum", {})),
        "firsat_skoru": props.get("Firsat Skoru", {}).get("number") or 0,
        "website": props.get("Web Sitesi", {}).get("url"),
        "telefon": props.get("Telefon", {}).get("phone_number"),
        "kaynak": _get_select(props.get("Kaynak", {})),
        "audit_ozeti": _get_rich(props.get("Audit Ozeti", {})),
        "hook_tipi": _get_select(props.get("Hook Tipi", {})),
        "gonderilen_mesaj": _get_rich(props.get("Gonderilen Mesaj", {})),
        "mesaj_versiyonu": _get_select(props.get("Mesaj Versiyonu", {})),
        "ilk_temas": (props.get("Ilk Temas", {}).get("date") or {}).get("start"),
        "son_aktivite": (props.get("Son Aktivite", {}).get("date") or {}).get("start"),
        "notlar": _get_rich(props.get("Notlar", {})),
    }
