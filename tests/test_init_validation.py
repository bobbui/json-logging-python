"""Argument validation and error paths of the public initialisation API (issue #137)."""
import logging

import pytest
from helpers.imports import undo_imports_from_package


@pytest.fixture
def fresh_json_logging():
    """Import a pristine json_logging so module level init state does not leak between tests."""
    undo_imports_from_package("json_logging")
    import json_logging
    yield json_logging
    undo_imports_from_package("json_logging")


def test_init_framework_twice_raises(fresh_json_logging):
    fresh_json_logging.init_flask()
    with pytest.raises(RuntimeError, match="more than once"):
        fresh_json_logging.init_flask()


def test_init_rejects_custom_formatter_that_is_not_a_formatter(fresh_json_logging):
    with pytest.raises(ValueError, match="custom_formatter"):
        fresh_json_logging.init_non_web(custom_formatter=dict)


def test_init_rejects_unknown_framework(fresh_json_logging):
    with pytest.raises(RuntimeError, match="not a supported framework"):
        fresh_json_logging.init_non_web(framework_name="no-such-framework")


def test_init_request_instrument_before_init_raises(fresh_json_logging):
    with pytest.raises(RuntimeError, match="init the logging first"):
        fresh_json_logging.init_request_instrument(app=object())


def test_init_request_instrument_after_non_web_init_raises(fresh_json_logging):
    fresh_json_logging.init_non_web()
    with pytest.raises(RuntimeError, match="init the logging first"):
        fresh_json_logging.init_request_instrument(app=object())


def test_init_request_instrument_rejects_bad_custom_formatter(fresh_json_logging):
    fresh_json_logging.init_flask()
    with pytest.raises(ValueError, match="custom_formatter"):
        fresh_json_logging.init_request_instrument(app=object(), custom_formatter=dict)


def test_init_request_instrument_rejects_bad_request_response_dto_class(fresh_json_logging):
    fresh_json_logging.init_flask()
    with pytest.raises(ValueError, match="request_response_dto_class"):
        fresh_json_logging.init_request_instrument(app=object(), request_response_dto_class=dict)


def test_get_request_logger_before_init_raises(fresh_json_logging):
    with pytest.raises(RuntimeError, match="only available"):
        fresh_json_logging.get_request_logger()


def test_config_root_logger_without_handlers_logs_error_and_returns(fresh_json_logging, monkeypatch):
    fresh_json_logging.ENABLE_JSON_LOGGING = True
    monkeypatch.setattr(logging.root, "handlers", [])
    errors = []
    monkeypatch.setattr(fresh_json_logging._logger, "error", lambda msg, *a, **kw: errors.append(msg))

    def fail(*args, **kwargs):
        raise AssertionError("root logger must not be touched when it has no handlers")

    monkeypatch.setattr(fresh_json_logging.util, "update_formatter_for_loggers", fail)

    fresh_json_logging.config_root_logger()

    assert len(errors) == 1
    assert "No logging handlers found" in errors[0]


def test_config_root_logger_switches_root_handlers_to_json(fresh_json_logging, monkeypatch):
    handler = logging.StreamHandler()
    monkeypatch.setattr(logging.root, "handlers", [handler])
    fresh_json_logging.init_non_web(enable_json=True)
    handler.setFormatter(logging.Formatter())  # undo what init_non_web already did to the handler

    fresh_json_logging.config_root_logger()

    assert isinstance(handler.formatter, fresh_json_logging.JSONLogFormatter)
