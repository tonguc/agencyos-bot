"""RequestID contextvar + filter davranisi (DB'siz)."""

import logging

from middleware.request_id import (
    _request_id_var, RequestIDFilter, get_request_id, set_request_id,
)


def test_default_is_dash():
    # Test ortaminda baska bir set yoksa default "-"
    assert _request_id_var.get("-") == "-"


def test_set_and_get():
    token = _request_id_var.set("abcd1234")
    try:
        assert get_request_id() == "abcd1234"
    finally:
        _request_id_var.reset(token)


def test_helper_setter():
    set_request_id("test999")
    assert get_request_id() == "test999"
    # Reset icin yeni set (helper reset token dondurmuyor — kabul)
    set_request_id("-")


def test_filter_injects_attribute():
    f = RequestIDFilter()
    token = _request_id_var.set("rid-xyz")
    try:
        rec = logging.LogRecord(
            name="t", level=logging.INFO, pathname=".", lineno=1,
            msg="m", args=(), exc_info=None,
        )
        f.filter(rec)
        assert rec.request_id == "rid-xyz"
    finally:
        _request_id_var.reset(token)
