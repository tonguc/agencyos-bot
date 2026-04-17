import os
import asyncio
import logging
import requests

logger = logging.getLogger(__name__)

NETGSM_API_URL = "https://api.netgsm.com.tr/sms/send/get/"

_ERROR_CODES = {
    "01": "Kullanıcı kodu veya şifre hatalı",
    "02": "Mesaj metni hatalı veya boş",
    "03": "Kullanıcı kodu veya şifre hatalı",
    "04": "Mesaj başlığı (header) kayıtlı değil",
    "05": "Gönderim kotası aşıldı",
    "06": "Gönderim durduruldu",
    "20": "Mesaj çok uzun",
    "30": "Geçersiz alıcı numarası",
    "70": "Hatalı API sorgusu",
}


def is_configured() -> bool:
    return all(
        os.getenv(k)
        for k in ("NETGSM_USERCODE", "NETGSM_PASSWORD", "NETGSM_HEADER")
    )


def _normalize_phone(phone: str) -> str:
    gsm = phone.replace("+", "").replace(" ", "").replace("-", "")
    if gsm.startswith("0"):
        gsm = "90" + gsm[1:]
    elif not gsm.startswith("90"):
        gsm = "90" + gsm
    return gsm


def _send_sync(phone: str, message: str) -> dict:
    params = {
        "usercode": os.getenv("NETGSM_USERCODE"),
        "password": os.getenv("NETGSM_PASSWORD"),
        "gsmno": _normalize_phone(phone),
        "text": message,
        "msgheader": os.getenv("NETGSM_HEADER"),
    }
    resp = requests.get(NETGSM_API_URL, params=params, timeout=15)
    body = resp.text.strip()
    parts = body.split()
    code = parts[0] if parts else body

    if code == "00":
        job_id = parts[1] if len(parts) > 1 else ""
        logger.info("NetGSM SMS gönderildi: %s (job=%s)", params["gsmno"], job_id)
        return {"success": True, "message": "SMS gönderildi", "job_id": job_id}

    err = _ERROR_CODES.get(code, f"Bilinmeyen hata kodu: {body}")
    logger.error("NetGSM hata: %s — %s", code, err)
    return {"success": False, "message": err, "code": code}


async def send_sms(phone: str, message: str) -> dict:
    """Send SMS via NetGSM. Returns {"success": bool, "message": str, ...}"""
    if not is_configured():
        return {
            "success": False,
            "message": "NetGSM yapılandırılmamış (NETGSM_USERCODE, NETGSM_PASSWORD, NETGSM_HEADER eksik)",
        }
    try:
        return await asyncio.to_thread(_send_sync, phone, message)
    except Exception as e:
        logger.error("NetGSM bağlantı hatası: %s", e)
        return {"success": False, "message": f"Bağlantı hatası: {e}"}
