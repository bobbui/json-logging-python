"""Test suite for the quart backend (issue #137)."""
import asyncio
import json
import logging

import pytest
import quart
from helpers.handler import FormattedMessageCollectorHandler
from helpers.imports import undo_imports_from_package

LOGGER_NAME = "quart-test"
REQUEST_LOGGER_NAME = "quart-request-logger"


@pytest.fixture
def app_and_handlers():
    import json_logging
    from json_logging.formatters import JSONRequestLogFormatter

    app = quart.Quart(__name__)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    log_handler = FormattedMessageCollectorHandler()
    logger.addHandler(log_handler)

    request_logger = logging.getLogger(REQUEST_LOGGER_NAME)
    request_handler = FormattedMessageCollectorHandler()
    request_handler.setFormatter(JSONRequestLogFormatter())

    json_logging.init_quart(enable_json=True)
    json_logging.init_request_instrument(app, exclude_url_patterns=["^/no-request-instrumentation"])
    request_logger.addHandler(request_handler)

    @app.route("/log")
    async def log():
        logger.info("info message")
        return {}

    @app.route("/get-correlation-id")
    async def get_correlation_id():
        return {"correlation_id": json_logging.get_correlation_id()}

    @app.route("/no-request-instrumentation")
    async def excluded():
        return {}

    yield app, log_handler, request_handler

    logger.removeHandler(log_handler)
    request_logger.removeHandler(request_handler)
    undo_imports_from_package("json_logging")


def _get(app, path, **kwargs):
    async def run():
        return await app.test_client().get(path, **kwargs)

    return asyncio.run(run())


def test_log_inside_request_has_given_correlation_id(app_and_handlers):
    app, log_handler, _ = app_and_handlers

    response = _get(app, "/log", headers={"X-Correlation-Id": "abc-def"})

    assert response.status_code == 200
    msg = json.loads(log_handler.messages[0])
    assert msg["msg"] == "info message"
    assert msg["correlation_id"] == "abc-def"


def test_get_correlation_id_returns_given_header(app_and_handlers):
    app, _, _ = app_and_handlers

    response = _get(app, "/get-correlation-id", headers={"X-Correlation-Id": "abc-def"})

    assert asyncio.run(response.get_json()) == {"correlation_id": "abc-def"}


def test_request_instrumentation_writes_request_log(app_and_handlers):
    app, _, request_handler = app_and_handlers

    response = _get(app, "/log")

    assert response.status_code == 200
    assert len(request_handler.messages) == 1
    msg = json.loads(request_handler.messages[0])
    assert msg["method"] == "GET"
    assert msg["request"] == "/log"
    assert msg["response_status"] == 200
    assert msg["type"] == "request"


def test_excluded_url_is_not_request_logged(app_and_handlers):
    app, _, request_handler = app_and_handlers

    response = _get(app, "/no-request-instrumentation")

    assert response.status_code == 200
    assert request_handler.messages == []


def test_init_request_instrument_rejects_non_quart_app(app_and_handlers):
    import json_logging

    with pytest.raises(RuntimeError, match="not a valid quart"):
        json_logging.init_request_instrument(object())
