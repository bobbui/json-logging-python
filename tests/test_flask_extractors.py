"""Request and response info extraction for the flask and connexion backends (issue #137)."""
import base64
import json
import logging
from types import SimpleNamespace

import flask
import pytest
from helpers.handler import FormattedMessageCollectorHandler
from helpers.imports import undo_imports_from_package


@pytest.fixture
def flask_app_and_request_handler():
    import json_logging
    from json_logging.formatters import JSONRequestLogFormatter

    app = flask.Flask(__name__)
    request_logger = logging.getLogger("flask-request-logger")
    handler = FormattedMessageCollectorHandler()
    handler.setFormatter(JSONRequestLogFormatter())

    json_logging.init_flask(enable_json=True)
    json_logging.init_request_instrument(app)
    request_logger.addHandler(handler)

    @app.route("/hello")
    def hello():
        return {"hello": "world"}

    yield app, handler

    request_logger.removeHandler(handler)
    undo_imports_from_package("json_logging")


def test_flask_request_log_has_request_and_response_details(flask_app_and_request_handler):
    app, handler = flask_app_and_request_handler

    response = app.test_client().get("/hello", headers={"X-Correlation-Id": "abc-def"})

    assert response.status_code == 200
    msg = json.loads(handler.messages[0])
    assert msg["method"] == "GET"
    assert msg["request"] == "/hello"
    assert msg["protocol"] == "HTTP/1.1"
    assert msg["correlation_id"] == "abc-def"
    assert msg["response_status"] == 200
    assert msg["response_content_type"] == "application/json"
    assert msg["response_size_b"] == len(response.data)
    assert msg["remote_user"] == "-"


def test_flask_request_log_has_basic_auth_user(flask_app_and_request_handler):
    app, handler = flask_app_and_request_handler
    token = base64.b64encode(b"alice:secret").decode()

    app.test_client().get("/hello", headers={"Authorization": "Basic " + token})

    assert json.loads(handler.messages[0])["remote_user"] == "alice"


def test_flask_init_request_instrument_rejects_non_flask_app(flask_app_and_request_handler):
    import json_logging

    with pytest.raises(RuntimeError, match="not a valid flask"):
        json_logging.init_request_instrument(object())


def test_flask_extractor_outside_request_context_has_no_current_request(flask_app_and_request_handler):
    from json_logging.framework.flask import FlaskRequestInfoExtractor

    assert FlaskRequestInfoExtractor.get_current_request() is None


def test_flask_extractor_header_lookup_falls_back_to_default(flask_app_and_request_handler):
    from json_logging.framework.flask import FlaskRequestInfoExtractor

    extractor = FlaskRequestInfoExtractor()
    request = SimpleNamespace(headers={"X-Present": "yes"})

    assert extractor.get_http_header(request, "X-Present") == "yes"
    assert extractor.get_http_header(request, "X-Missing", "fallback") == "fallback"
    # an object without usable headers must not raise
    assert extractor.get_http_header(object(), "X-Missing", "fallback") == "fallback"


def test_flask_extractor_correlation_id_outside_request_context_is_none(flask_app_and_request_handler):
    from json_logging.framework.flask import FlaskRequestInfoExtractor

    extractor = FlaskRequestInfoExtractor()

    extractor.set_correlation_id(None, "ignored")  # no app context: must not raise
    assert extractor.get_correlation_id_in_request_context(None) is None
