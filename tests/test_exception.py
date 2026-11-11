from __future__ import annotations

import sys

import pytest

from us_visa.exception import USvisaException, error_message_detail


def test_error_message_detail_includes_file_and_line() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        message = error_message_detail(ValueError("boom"), sys)

    assert "line number" in message
    assert "test_exception.py" in message
    assert "boom" in message


def test_error_message_detail_without_active_traceback() -> None:
    assert error_message_detail("plain failure", sys) == "Error occurred: plain failure"


def test_usvisa_exception_preserves_message_and_cause() -> None:
    try:
        try:
            {}["missing"]
        except KeyError as original:
            raise USvisaException(original, sys) from original
    except USvisaException as exc:
        assert "missing" in str(exc)
        assert "test_exception.py" in str(exc)
        assert isinstance(exc.__cause__, KeyError)


def test_usvisa_exception_is_an_exception() -> None:
    with pytest.raises(USvisaException):
        raise USvisaException("failed", sys)
