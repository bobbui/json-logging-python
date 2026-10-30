"""Tests for reading the request body from a custom request formatter (FastAPI)"""
import json
import logging
import re

import fastapi
import fastapi.testclient
import pytest
import starlette
from helpers.handler import FormattedMessageCollectorHandler
from helpers.imports import undo_imports_from_package


def _starlette_can_capture_body():
    return tuple(int(part) for part in re.findall(r"\d+", starlette.__version__)[:2]) >= (0, 28)


needs_body_capture = pytest.mark.skipif(
    not _starlette_can_capture_body(), reason="read_request_body needs starlette >= 0.28"
)


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
    if not _starlette_can_capture_body():
        pytest.skip("read_request_body needs starlette >= 0.28")
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


def test_read_request_body_is_rejected_on_starlette_that_would_hang(monkeypatch):
    import starlette
    import json_logging

    try:
        json_logging.init_fastapi(enable_json=True)
        monkeypatch.setattr(starlette, "__version__", "0.27.0")
        with pytest.raises(RuntimeError, match="starlette >= 0.28"):
            json_logging.init_request_instrument(fastapi.FastAPI(), read_request_body=True)
    finally:
        undo_imports_from_package("json_logging")


@needs_body_capture
def test_response_time_includes_reading_the_body(monkeypatch):
    """The request timer starts before the body is read, not after."""
    import json_logging

    client, handler, request_logger = _build_client(read_request_body=True)
    try:
        events = []
        dto_class = json_logging.framework.fastapi.implementation._request_config_class
        original_init = dto_class.__init__

        def recording_init(self, request, **kwargs):
            events.append("timer started")
            original_init(self, request, **kwargs)

        monkeypatch.setattr(dto_class, "__init__", recording_init)
        original_body = fastapi.Request.body

        async def recording_body(self):
            events.append("body read")
            return await original_body(self)

        monkeypatch.setattr(fastapi.Request, "body", recording_body)

        client.post("/echo", content=b"x")

        assert events.index("timer started") < events.index("body read")
    finally:
        request_logger.removeHandler(handler)
        undo_imports_from_package("json_logging")
