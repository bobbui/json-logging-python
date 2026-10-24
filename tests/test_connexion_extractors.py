"""Request and response info extraction for the connexion backend (issue #137)."""
from types import SimpleNamespace

import pytest
from helpers.imports import undo_imports_from_package


@pytest.fixture
def connexion_extractors():
    import json_logging
    from json_logging.framework import connexion as connexion_framework

    yield json_logging, connexion_framework
    undo_imports_from_package("json_logging")


def _request(**overrides):
    values = dict(
        authorization=None,
        headers={"X-Present": "yes"},
        environ={"SERVER_PROTOCOL": "HTTP/1.1", "REMOTE_PORT": "5555"},
        path="/hello",
        content_length=12,
        method="POST",
        remote_addr="10.0.0.1",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_init_request_instrument_rejects_non_connexion_app(connexion_extractors):
    json_logging, _ = connexion_extractors
    json_logging.init_connexion()

    with pytest.raises(RuntimeError, match="not a valid connexion"):
        json_logging.init_request_instrument(SimpleNamespace(app=object()))


def test_remote_user_defaults_to_empty_value(connexion_extractors):
    json_logging, framework = connexion_extractors

    assert framework.ConnexionRequestInfoExtractor().get_remote_user(_request()) == json_logging.EMPTY_VALUE


def test_remote_user_is_the_basic_auth_username(connexion_extractors):
    _, framework = connexion_extractors
    request = _request(authorization=SimpleNamespace(username="alice"))

    assert framework.ConnexionRequestInfoExtractor().get_remote_user(request) == "alice"


def test_header_lookup_falls_back_to_default(connexion_extractors):
    _, framework = connexion_extractors
    extractor = framework.ConnexionRequestInfoExtractor()

    assert extractor.get_http_header(_request(), "X-Present") == "yes"
    assert extractor.get_http_header(_request(), "X-Missing", "fallback") == "fallback"
    assert extractor.get_http_header(object(), "X-Missing", "fallback") == "fallback"


def test_request_fields_are_read_from_the_request(connexion_extractors):
    _, framework = connexion_extractors
    extractor = framework.ConnexionRequestInfoExtractor()
    request = _request()

    assert extractor.get_protocol(request) == "HTTP/1.1"
    assert extractor.get_path(request) == "/hello"
    assert extractor.get_content_length(request) == 12
    assert extractor.get_method(request) == "POST"
    assert extractor.get_remote_ip(request) == "10.0.0.1"
    assert extractor.get_remote_port(request) == "5555"


def test_response_fields_are_read_from_the_response(connexion_extractors):
    _, framework = connexion_extractors
    extractor = framework.ConnexionResponseInfoExtractor()
    response = SimpleNamespace(
        status_code=201, calculate_content_length=lambda: 42, content_type="application/json")

    assert extractor.get_status_code(response) == 201
    assert extractor.get_response_size(response) == 42
    assert extractor.get_content_type(response) == "application/json"
