"""Configurable exclusion of JSON output fields (issue #98)."""
import io
import json
import logging

import pytest
from helpers.handler import FormattedMessageCollectorHandler
from helpers.imports import undo_imports_from_package


@pytest.fixture
def fresh_json_logging():
    undo_imports_from_package("json_logging")
    yield
    undo_imports_from_package("json_logging")


def _capture(logger_name, formatter):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = FormattedMessageCollectorHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger, handler


def _release(logger, handler):
    logger.removeHandler(handler)


def test_default_output_keeps_every_standard_field(fresh_json_logging):
    import json_logging
    assert json_logging.EXCLUDED_FIELDS == ()
    json_logging.init_non_web(enable_json=True)
    logger, handler = _capture("excl-default", json_logging.JSONLogFormatter())
    try:
        logger.info("hello")
    finally:
        _release(logger, handler)
    record = json.loads(handler.messages[0])
    for field in ("written_at", "written_ts", "msg", "type", "logger", "thread", "level", "module", "line_no"):
        assert field in record, field


def test_excluding_written_ts_removes_only_that_field(fresh_json_logging):
    import json_logging
    json_logging.EXCLUDED_FIELDS = ["written_ts"]
    json_logging.init_non_web(enable_json=True)
    logger, handler = _capture("excl-one", json_logging.JSONLogFormatter())
    try:
        logger.info("hello")
    finally:
        _release(logger, handler)
    record = json.loads(handler.messages[0])
    assert "written_ts" not in record
    assert record["written_at"] and record["msg"] == "hello" and record["type"] == "log"


def test_excluding_several_fields_keeps_the_rest(fresh_json_logging):
    import json_logging
    json_logging.EXCLUDED_FIELDS = ("written_ts", "thread", "module")
    json_logging.init_non_web(enable_json=True)
    logger, handler = _capture("excl-many", json_logging.JSONLogFormatter())
    try:
        logger.info("hello")
    finally:
        _release(logger, handler)
    record = json.loads(handler.messages[0])
    assert not {"written_ts", "thread", "module"} & set(record)
    assert {"written_at", "msg", "type", "logger", "level", "line_no"} <= set(record)


def test_empty_exclusion_list_is_the_same_as_the_default(fresh_json_logging):
    import json_logging
    json_logging.EXCLUDED_FIELDS = []
    json_logging.init_non_web(enable_json=True)
    logger, handler = _capture("excl-empty", json_logging.JSONLogFormatter())
    try:
        logger.info("hello")
    finally:
        _release(logger, handler)
    assert "written_ts" in json.loads(handler.messages[0])


def test_web_formatter_honours_exclusion_and_keeps_correlation_id(fresh_json_logging):
    import flask
    import json_logging
    json_logging.EXCLUDED_FIELDS = ["written_ts"]
    app = flask.Flask(__name__)
    json_logging.init_flask(enable_json=True)
    json_logging.init_request_instrument(app)
    logger, handler = _capture("excl-web", json_logging.JSONLogWebFormatter())
    try:
        with app.test_request_context("/", headers={"X-Correlation-ID": "kept-1"}):
            logger.info("in request")
    finally:
        _release(logger, handler)
    record = json.loads(handler.messages[0])
    assert "written_ts" not in record
    assert record["correlation_id"] == "kept-1"


def test_request_log_formatter_honours_exclusion(fresh_json_logging):
    import flask
    import json_logging
    json_logging.EXCLUDED_FIELDS = ("written_ts", "response_time_ms")
    app = flask.Flask(__name__)
    json_logging.init_flask(enable_json=True)
    json_logging.init_request_instrument(app)
    buf = io.StringIO()
    request_logger = json_logging.get_request_logger()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(json_logging.JSONRequestLogFormatter())
    request_logger.handlers = [handler]
    app.test_client().get("/nothing-here")
    record = json.loads(buf.getvalue().splitlines()[0])
    assert "written_ts" not in record and "response_time_ms" not in record
    assert record["type"] == "request" and "response_status" in record


def test_extra_and_props_fields_are_excluded_too(fresh_json_logging):
    import json_logging
    json_logging.EXCLUDED_FIELDS = ["secret_token", "tenant"]
    json_logging.init_non_web(enable_json=True)
    logger, handler = _capture("excl-extra", json_logging.JSONLogFormatter())
    try:
        logger.info("hello", extra={"secret_token": "abc", "props": {"tenant": "acme", "job": "j1"}})
    finally:
        _release(logger, handler)
    record = json.loads(handler.messages[0])
    assert "secret_token" not in record and "tenant" not in record
    assert record["job"] == "j1"


def test_custom_formatter_subclass_inherits_exclusion(fresh_json_logging):
    import json_logging

    class Custom(json_logging.JSONLogFormatter):
        def _format_log_object(self, record, request_util):
            obj = super()._format_log_object(record, request_util)
            obj["custom"] = "yes"
            return obj

    json_logging.EXCLUDED_FIELDS = ["written_ts"]
    json_logging.init_non_web(enable_json=True, custom_formatter=Custom)
    logger, handler = _capture("excl-custom", Custom())
    try:
        logger.info("hello")
    finally:
        _release(logger, handler)
    record = json.loads(handler.messages[0])
    assert "written_ts" not in record and record["custom"] == "yes"


def test_formatter_created_before_the_setting_keeps_its_original_configuration(fresh_json_logging):
    """Settings are read when a formatter is constructed, like the existing COMPONENT_* settings."""
    import json_logging
    early = json_logging.JSONLogFormatter()
    json_logging.EXCLUDED_FIELDS = ["written_ts"]
    late = json_logging.JSONLogFormatter()
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "m", None, None)
    assert "written_ts" in json.loads(early.format(record))
    assert "written_ts" not in json.loads(late.format(record))


@pytest.mark.parametrize("bad", ["written_ts", None, 42, ["written_ts", 7], [b"written_ts"]])
def test_invalid_configuration_is_rejected_when_a_formatter_is_built(fresh_json_logging, bad):
    import json_logging
    json_logging.EXCLUDED_FIELDS = bad
    with pytest.raises(TypeError):
        json_logging.JSONLogFormatter()
