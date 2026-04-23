"""Request ID middleware + logging context.

Her request icin kisa bir correlation ID uretilir (veya client'tan gelen
X-Request-ID kullanilir). ContextVar ile logging formatter bu ID'yi
"req=abcd1234" olarak her log satirina ekler — multi-step akislarda (API
-> service -> Claude -> DB) log'lar arasi bag kurulur.
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id_var.get()


def set_request_id(rid: str) -> None:
    """ARQ task'lari gibi request disi baglamlarda manuel set icin."""
    _request_id_var.set(rid)


class RequestIDFilter(logging.Filter):
    """Log record'lara request_id attribute'unu enjekte eder."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get()
        return True


class RequestIDMiddleware(BaseHTTPMiddleware):
    """X-Request-ID header'ini oku (yoksa uret), contextvar'a yaz, response'a geri ekle."""

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get("X-Request-ID")
        rid = (incoming or uuid.uuid4().hex)[:12]
        token = _request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            _request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        return response
