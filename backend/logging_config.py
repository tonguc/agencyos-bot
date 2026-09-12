import logging
import sys
from logging.handlers import RotatingFileHandler

from middleware.request_id import RequestIDFilter


def setup_logging(level: str = "INFO", log_file: str = "agencyos.log") -> None:
    # request_id middleware ContextVar'dan geliyor; "-" default (request disi).
    fmt = "%(asctime)s | %(levelname)-8s | req=%(request_id)s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        # Rotasyon: 100MB/file, 5 backup (~500MB cap) — disk dolmasini engeller.
        handlers.append(
            RotatingFileHandler(
                log_file,
                encoding="utf-8",
                maxBytes=100 * 1024 * 1024,
                backupCount=5,
            )
        )

    rid_filter = RequestIDFilter()
    for h in handlers:
        h.addFilter(rid_filter)

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=datefmt,
        handlers=handlers,
    )

    # Quieten noisy third-party loggers
    for noisy in ("httpx", "httpcore", "sqlalchemy.engine", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
