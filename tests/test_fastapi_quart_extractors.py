"""Request info extraction for the fastapi and quart backends (issue #137)."""
from types import SimpleNamespace

import pytest
from helpers.imports import undo_imports_from_package


@pytest.fixture
def fresh_json_logging():
    import json_logging

    yield json_logging
    undo_imports_from_package("json_logging")


class _BrokenHeaders:
    """Headers whose membership test fails, like a request that is already closed."""

    def __contains__(self, item):
        raise RuntimeError("headers unavailable")


def test_fastapi_init_request_instrument_rejects_non_fastapi_app(fresh_json_logging):
    fresh_json_logging.init_fastapi()

    with pytest.raises(RuntimeError, match="not a valid fastapi"):
        fresh_json_logging.init_request_instrument(object())


def test_fastapi_protocol_is_built_from_scope(fresh_json_logging):
    from json_logging.framework.fastapi.implementation import FastAPIRequestInfoExtractor

    extractor = FastAPIRequestInfoExtractor()
    http = SimpleNamespace(scope={"type": "http", "http_version": "1.1"})

    assert extractor.get_protocol(http) == "HTTP/1.1"


@pytest.mark.parametrize("scope", [{"type": "http"}, {"type": "websocket", "http_version": "1.1"}, {}])
def test_fastapi_protocol_falls_back_to_empty_value(fresh_json_logging, scope):
    from json_logging.framework.fastapi.implementation import FastAPIRequestInfoExtractor

    extractor = FastAPIRequestInfoExtractor()

    assert extractor.get_protocol(SimpleNamespace(scope=scope)) == fresh_json_logging.EMPTY_VALUE


def test_fastapi_header_lookup_falls_back_to_default(fresh_json_logging):
    from json_logging.framework.fastapi.implementation import FastAPIRequestInfoExtractor

    extractor = FastAPIRequestInfoExtractor()

    assert extractor.get_http_header(SimpleNamespace(headers={"X-Present": "yes"}), "X-Present") == "yes"
    assert extractor.get_http_header(SimpleNamespace(headers={}), "X-Missing", "fallback") == "fallback"
    assert extractor.get_http_header(SimpleNamespace(headers=_BrokenHeaders()), "X", "fallback") == "fallback"


def test_quart_remote_user(fresh_json_logging):
    from json_logging.framework.quart import QuartRequestInfoExtractor

    extractor = QuartRequestInfoExtractor()

    assert extractor.get_remote_user(SimpleNamespace(authorization=None)) == fresh_json_logging.EMPTY_VALUE
    assert extractor.get_remote_user(SimpleNamespace(authorization=SimpleNamespace(username="alice"))) == "alice"


def test_quart_header_lookup_falls_back_to_default(fresh_json_logging):
    from json_logging.framework.quart import QuartRequestInfoExtractor

    extractor = QuartRequestInfoExtractor()

    assert extractor.get_http_header(SimpleNamespace(headers={"X-Present": "yes"}), "X-Present") == "yes"
    assert extractor.get_http_header(SimpleNamespace(headers={}), "X-Missing", "fallback") == "fallback"
    assert extractor.get_http_header(SimpleNamespace(headers=_BrokenHeaders()), "X", "fallback") == "fallback"


def test_quart_correlation_id_outside_request_context_is_none(fresh_json_logging):
    from json_logging.framework.quart import QuartRequestInfoExtractor

    extractor = QuartRequestInfoExtractor()

    extractor.set_correlation_id(None, "ignored")  # no app context: must not raise
    assert extractor.get_correlation_id_in_request_context(None) is None


def test_quart_request_fields_are_read_from_the_request(fresh_json_logging):
    from json_logging.framework.quart import QuartRequestInfoExtractor

    extractor = QuartRequestInfoExtractor()
    request = SimpleNamespace(
        scheme="https", path="/hello", content_length=12, method="POST", remote_addr="10.0.0.1", host="example.com:8443")

    assert extractor.get_protocol(request) == "https"
    assert extractor.get_path(request) == "/hello"
    assert extractor.get_content_length(request) == 12
    assert extractor.get_method(request) == "POST"
    assert extractor.get_remote_ip(request) == "10.0.0.1"
    assert extractor.get_remote_port(request) == "8443"
    assert extractor.get_remote_port(SimpleNamespace(host="example.com")) is None
