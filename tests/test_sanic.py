"""Test suite for the sanic backend (issue #137)."""
import json
import logging

import pytest
import sanic
import sanic.response
from helpers.handler import FormattedMessageCollectorHandler
from helpers.imports import undo_imports_from_package

LOGGER_NAME = "sanic-test"
REQUEST_LOGGER_NAME = "sanic-request"


@pytest.fixture
def app_and_handlers():
    import json_logging
    from json_logging.formatters import JSONRequestLogFormatter

    app = sanic.Sanic("json-logging-sanic-test")

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    log_handler = FormattedMessageCollectorHandler()
    logger.addHandler(log_handler)

    request_logger = logging.getLogger(REQUEST_LOGGER_NAME)
    request_handler = FormattedMessageCollectorHandler()
    request_handler.setFormatter(JSONRequestLogFormatter())

    json_logging.init_sanic(enable_json=True)
    json_logging.init_request_instrument(app, exclude_url_patterns=["^/no-request-instrumentation"])
    request_logger.addHandler(request_handler)

    @app.route("/log")
    async def log(request):
        logger.info("info message")
        return sanic.response.json({})

    @app.route("/get-correlation-id")
    async def get_correlation_id(request):
        return sanic.response.json({"correlation_id": json_logging.get_correlation_id(request)})

    @app.route("/no-request-instrumentation")
    async def excluded(request):
        return sanic.response.json({})

    yield app, log_handler, request_handler

    logger.removeHandler(log_handler)
    request_logger.removeHandler(request_handler)
    undo_imports_from_package("json_logging")
    sanic.Sanic._app_registry.pop("json-logging-sanic-test", None)


def test_get_correlation_id_returns_given_header(app_and_handlers):
    app, _, _ = app_and_handlers

    _, response = app.test_client.get("/get-correlation-id", headers={"X-Correlation-Id": "abc-def"})

    assert response.json == {"correlation_id": "abc-def"}


def test_get_correlation_id_is_generated_when_missing(app_and_handlers):
    app, _, _ = app_and_handlers

    _, response = app.test_client.get("/get-correlation-id")

    assert response.json["correlation_id"] not in (None, "-", "")


def test_request_instrumentation_writes_request_log(app_and_handlers):
    app, _, request_handler = app_and_handlers

    _, response = app.test_client.get("/log")

    assert response.status == 200
    assert len(request_handler.messages) == 1
    msg = json.loads(request_handler.messages[0])
    assert msg["method"] == "GET"
    assert msg["request"] == "/log"
    assert msg["response_status"] == 200
    assert msg["type"] == "request"


def test_excluded_url_is_not_request_logged(app_and_handlers):
    app, _, request_handler = app_and_handlers

    _, response = app.test_client.get("/no-request-instrumentation")

    assert response.status == 200
    assert request_handler.messages == []


def test_init_request_instrument_rejects_non_sanic_app(app_and_handlers):
    import json_logging

    with pytest.raises(RuntimeError, match="not a valid Sanic"):
        json_logging.init_request_instrument(object())
