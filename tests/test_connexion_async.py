"""Request instrumentation for Connexion 3 AsyncApp, which runs without Flask (issue #96)."""
import json
import logging
import sys

import pytest
from helpers import constants
from helpers.handler import FormattedMessageCollectorHandler
from helpers.imports import undo_imports_from_package

connexion = pytest.importorskip("connexion")
if not hasattr(connexion, "AsyncApp"):
    pytest.skip("connexion.AsyncApp needs Connexion 3", allow_module_level=True)

from connexion.resolver import Resolver  # noqa: E402

LOGGER_NAME = "connexion-async-test"


@pytest.fixture(params=["with flask", "without flask"])
def client_and_log_handlers(request, monkeypatch):
    if request.param == "without flask":
        # Connexion 3 installed without its flask extra: AsyncApp must work without importing flask
        monkeypatch.setitem(sys.modules, "flask", None)
    import json_logging

    app = connexion.AsyncApp(__name__)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    handler = FormattedMessageCollectorHandler()
    logger.addHandler(handler)

    request_logger = logging.getLogger("connexion-request-logger")
    request_handler = FormattedMessageCollectorHandler()
    request_logger.addHandler(request_handler)

    json_logging.init_connexion(enable_json=True)
    json_logging.init_request_instrument(app, exclude_url_patterns=["^/no-request-instrumentation"])

    async def log_async():
        logger.info("async message")
        return {"correlation_id": json_logging.get_correlation_id()}

    def log_sync():
        logger.info("sync message")
        return {"correlation_id": json_logging.get_correlation_id()}

    async def fail():
        raise RuntimeError("boom")

    async def excluded():
        return {}

    operations = {"log_async": log_async, "log_sync": log_sync, "fail": fail, "excluded": excluded}
    paths = {"/log/async": "log_async", "/log/sync": "log_sync", "/fail": "fail",
             "/no-request-instrumentation": "excluded"}
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "test", "version": "1"},
        "paths": {path: {"get": {"operationId": operation, "responses": {"200": {"description": "ok"}}}}
                  for path, operation in paths.items()},
    }
    app.add_api(spec, resolver=Resolver(function_resolver=operations.__getitem__))

    yield app.test_client(), handler, request_handler

    logger.removeHandler(handler)
    request_logger.removeHandler(request_handler)
    undo_imports_from_package("json_logging")


def test_request_is_logged(client_and_log_handlers):
    api_client, _, request_handler = client_and_log_handlers

    response = api_client.get("/log/async", headers={"X-Correlation-Id": "abc-def"})

    assert response.status_code == 200
    assert len(request_handler.messages) == 1
    msg = json.loads(request_handler.messages[0])
    assert msg["type"] == "request"
    assert msg["correlation_id"] == "abc-def"
    assert msg["request"] == "/log/async"
    assert msg["method"] == "GET"
    assert msg["protocol"] == "HTTP/1.1"
    assert msg["response_status"] == 200
    assert msg["response_content_type"] == "application/json"
    assert int(msg["response_size_b"]) == len(response.content)


@pytest.mark.parametrize("path", ["/log/async", "/log/sync"])
def test_handler_logs_share_the_request_correlation_id(client_and_log_handlers, path):
    api_client, handler, request_handler = client_and_log_handlers

    response = api_client.get(path)

    assert response.status_code == 200
    correlation_id = response.json()["correlation_id"]
    assert len(handler.messages) == 1
    msg = json.loads(handler.messages[0])
    assert set(msg.keys()) == constants.STANDARD_MSG_ATTRIBUTES
    assert msg["correlation_id"] == correlation_id
    assert json.loads(request_handler.messages[0])["correlation_id"] == correlation_id


def test_error_response_is_logged(client_and_log_handlers):
    api_client, _, request_handler = client_and_log_handlers

    response = api_client.get("/fail")

    assert response.status_code == 500
    assert len(request_handler.messages) == 1
    assert json.loads(request_handler.messages[0])["response_status"] == 500


def test_excluded_url_is_not_logged(client_and_log_handlers):
    api_client, _, request_handler = client_and_log_handlers

    response = api_client.get("/no-request-instrumentation")

    assert response.status_code == 200
    assert request_handler.messages == []
