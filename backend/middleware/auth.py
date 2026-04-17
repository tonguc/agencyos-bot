from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from config import settings

# Paths that bypass API key check
_EXEMPT: frozenset[str] = frozenset({
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
})


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXEMPT:
            return await call_next(request)

        key = request.headers.get("X-API-Key", "")
        if not key or key != settings.AGENCYOS_API_KEY:
            return JSONResponse(
                {"error": "Unauthorized", "detail": "X-API-Key header missing or invalid"},
                status_code=401,
            )

        return await call_next(request)
