"""notify_admin debounce + config gating."""

import pytest

from services.notify import notify_admin, _LAST_SENT


@pytest.fixture(autouse=True)
def reset_debounce():
    _LAST_SENT.clear()
    yield
    _LAST_SENT.clear()


async def test_no_token_silent(caplog):
    # TELEGRAM_BOT_TOKEN conftest'te bos -> fail-safe path
    import logging
    caplog.set_level(logging.INFO)
    await notify_admin("test mesaji")
    # Exception sizmamali; sadece info log beklenir
    assert any("atlandi" in r.message for r in caplog.records)


async def test_debounce_caches_second_call(caplog, monkeypatch):
    # Token + chat set et ama gonderim yerine debounce path'ini test et
    from config import settings as settings_module
    monkeypatch.setattr(settings_module, "TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setattr(settings_module, "ADMIN_TELEGRAM_CHAT_IDS", "12345")

    # requests.post mock — gercek HTTP call yapma
    sent_count = {"n": 0}
    def fake_post(*a, **kw):
        sent_count["n"] += 1
        class R:
            pass
        return R()
    monkeypatch.setattr("services.notify.requests.post", fake_post)

    text = "aynı mesaj"
    await notify_admin(text)
    await notify_admin(text)   # 10dk icinde -> debounced
    assert sent_count["n"] == 1
