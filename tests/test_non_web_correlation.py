"""Public correlation-ID accessor in non-web mode (issue #126).

init_non_web() does not create a request utility, so json_logging.get_correlation_id() used to raise
AttributeError. Non-web logs have no HTTP request, so the accessor should return the documented empty
value and must not generate an ID.
"""
import json
import logging

import pytest
from helpers.handler import FormattedMessageCollectorHandler
from helpers.imports import undo_imports_from_package


@pytest.fixture(autouse=True)
def restore_framework_logger_state():
    """Restore process-global logging defaults and per-logger state changed by initialization."""
    default_formatter = logging._defaultFormatter
    names = ("flask-request-logger", "connexion-request-logger", "quart-request-logger",
             "werkzeug", "non-web-test")
    saved = {}
    for name in names:
        logger = logging.getLogger(name)
        saved[name] = (list(logger.handlers), logger.level, logger.parent, logger.propagate, logger.disabled)
    yield
    logging._defaultFormatter = default_formatter
    for name, (handlers, level, parent, propagate, disabled) in saved.items():
        logger = logging.getLogger(name)
        logger.handlers = handlers
        logger.setLevel(level)
        logger.parent = parent
        logger.propagate = propagate
        logger.disabled = disabled


@pytest.fixture
def fresh_json_logging():
    undo_imports_from_package("json_logging")
    yield
    undo_imports_from_package("json_logging")


@pytest.mark.parametrize("enable_json", [True, False])
def test_get_correlation_id_after_init_non_web_returns_empty_value(fresh_json_logging, enable_json):
    import json_logging
    json_logging.init_non_web(enable_json=enable_json)

    assert json_logging.get_correlation_id() == json_logging.EMPTY_VALUE
    assert json_logging.get_correlation_id() == json_logging.EMPTY_VALUE  # no ID is generated or cached


def test_get_correlation_id_before_any_init_returns_empty_value(fresh_json_logging):
    import json_logging
    assert json_logging.get_correlation_id() == json_logging.EMPTY_VALUE


def test_non_web_json_logging_output_is_unchanged(fresh_json_logging):
    import json_logging
    json_logging.init_non_web(enable_json=True)

    logger = logging.getLogger("non-web-test")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = FormattedMessageCollectorHandler()
    handler.setFormatter(json_logging.JSONLogFormatter())
    logger.addHandler(handler)
    try:
        logger.info("hello %s", "world")
    finally:
        logger.removeHandler(handler)

    record = json.loads(handler.messages[0])
    assert record["type"] == "log"
    assert record["msg"] == "hello world"
    assert record["logger"] == "non-web-test"
    assert record["level"] == "INFO"
    assert "correlation_id" not in record  # non-web records never carry a correlation ID


def test_get_correlation_id_with_explicit_request_still_works_in_web_mode(fresh_json_logging):
    """Web mode keeps its behaviour: an explicitly supplied request is still honoured."""
    import flask
    import json_logging

    app = flask.Flask(__name__)
    json_logging.init_flask(enable_json=True)
    json_logging.init_request_instrument(app)
    with app.test_request_context("/", headers={"X-Correlation-ID": "web-1"}):
        assert json_logging.get_correlation_id() == "web-1"
        assert json_logging.get_correlation_id(request=flask.request) == "web-1"
