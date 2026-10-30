"""Tests for reading the request body from a custom request formatter (FastAPI)"""
import json
import logging

import fastapi
import fastapi.testclient
import pytest
from helpers.handler import FormattedMessageCollectorHandler
from helpers.imports import undo_imports_from_package


def _build_client(read_request_body, exclude_url_patterns=("^/excluded",)):
    import json_logging

    class BodyFormatter(json_logging.JSONRequestLogFormatter):
        """Adds the body to the request log, the way a user would in a synchronous formatter."""

        def _format_log_object(self, record, request_util):
            log_object = super()._format_log_object(record, request_util)
            request = record.request_response_data._request
            body = getattr(request.state, "json_logging_request_body", None)
            log_object["request_body"] = body.decode() if body is not None else None
            return log_object

    app = fastapi.FastAPI()
    json_logging.init_fastapi(enable_json=True)
    json_logging.init_request_instrument(
        app,
        custom_formatter=BodyFormatter,
        exclude_url_patterns=list(exclude_url_patterns),
        read_request_body=read_request_body,
    )

    @app.post("/echo")
    async def echo(request: fastapi.Request):
        return {"body": (await request.body()).decode()}

    @app.post("/echo-sync")
    def echo_sync(payload: dict):
        return payload

    @app.post("/excluded")
    async def excluded(request: fastapi.Request):
        return {"body": (await request.body()).decode()}

    request_logger = logging.getLogger("fastapi-request-logger")
    handler = FormattedMessageCollectorHandler()
    handler.setFormatter(request_logger.handlers[0].formatter)
    request_logger.addHandler(handler)
    return fastapi.testclient.TestClient(app), handler, request_logger


@pytest.fixture
def body_client():
    client, handler, request_logger = _build_client(read_request_body=True)
    yield client, handler
    request_logger.removeHandler(handler)
    undo_imports_from_package("json_logging")  # Necessary because of json-logging's global state


@pytest.fixture
def default_client():
    client, handler, request_logger = _build_client(read_request_body=False)
    yield client, handler
    request_logger.removeHandler(handler)
    undo_imports_from_package("json_logging")


def test_formatter_can_read_request_body(body_client):
    client, handler = body_client

    response = client.post("/echo", content=b"hello body")

    assert response.status_code == 200
    assert json.loads(handler.messages[0])["request_body"] == "hello body"


def test_endpoint_can_still_read_body_after_middleware(body_client):
    client, _ = body_client

    assert client.post("/echo", content=b"hello body").json() == {"body": "hello body"}


def test_sync_endpoint_with_parsed_body_still_works(body_client):
    client, handler = body_client

    response = client.post("/echo-sync", json={"a": 1})

    assert response.json() == {"a": 1}
    assert json.loads(json.loads(handler.messages[0])["request_body"]) == {"a": 1}


def test_empty_body_is_an_empty_string(body_client):
    client, handler = body_client

    client.post("/echo")

    assert json.loads(handler.messages[0])["request_body"] == ""


def test_body_is_not_read_by_default(default_client):
    client, handler = default_client

    response = client.post("/echo", content=b"hello body")

    assert response.json() == {"body": "hello body"}
    assert json.loads(handler.messages[0])["request_body"] is None


def test_excluded_url_body_is_not_read_for_logging(body_client):
    client, handler = body_client

    response = client.post("/excluded", content=b"secret")

    assert response.json() == {"body": "secret"}
    assert handler.messages == []


def test_each_request_gets_its_own_body(body_client):
    client, handler = body_client

    client.post("/echo", content=b"first")
    client.post("/echo", content=b"second")

    assert [json.loads(m)["request_body"] for m in handler.messages] == ["first", "second"]


def test_read_request_body_is_rejected_for_frameworks_that_do_not_support_it():
    import flask
    import json_logging

    try:
        json_logging.init_flask(enable_json=True)
        with pytest.raises(ValueError, match="read_request_body"):
            json_logging.init_request_instrument(flask.Flask(__name__), read_request_body=True)
    finally:
        undo_imports_from_package("json_logging")
