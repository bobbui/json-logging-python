"""Configurable exclusion of JSON output fields (issue #98)."""
import io
import json
import logging
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from helpers.handler import FormattedMessageCollectorHandler
from helpers.imports import undo_imports_from_package

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def fresh_json_logging():
    undo_imports_from_package("json_logging")
    yield
    undo_imports_from_package("json_logging")


def _logger_state(logger):
    return (list(logger.handlers), [h.formatter for h in logger.handlers], logger.level, logger.parent,
            logger.propagate, logger.disabled)


@pytest.fixture(autouse=True)
def restore_logging_state():
    """init_*() change process-wide logging state: logging._defaultFormatter, the formatter of every handler on
    every existing logger, and the framework loggers (handlers, parent, disabled). _capture() changes logger levels
    and propagation. Restore all of it after each test, also when the test fails, so tests cannot affect each
    other or other test modules. The root logger is left alone: init_*() do not change it, and pytest replaces
    its own capture handlers on it between test phases."""
    manager = logging.Logger.manager
    default_formatter = logging._defaultFormatter
    saved = {name: _logger_state(logger) for name, logger in manager.loggerDict.items()
             if isinstance(logger, logging.Logger)}
    yield
    logging._defaultFormatter = default_formatter
    for name, logger in list(manager.loggerDict.items()):
        if not isinstance(logger, logging.Logger):
            continue
        if name not in saved:              # created by the test: return it to a new logger's state
            for handler in list(logger.handlers):
                logger.removeHandler(handler)
                handler.close()
            logger.setLevel(logging.NOTSET)
            logger.propagate, logger.disabled = True, False
            if logger.parent is None:      # init_request_instrument() detaches the request logger
                logger.parent = logging.root
            continue
        _restore_logger(logger, saved[name])


def _restore_logger(logger, state):
    handlers, formatters, level, parent, propagate, disabled = state
    for handler in logger.handlers:
        if handler not in handlers:
            handler.close()
    logger.handlers = handlers
    for handler, formatter in zip(handlers, formatters):
        handler.setFormatter(formatter)
    logger.setLevel(level)
    logger.parent = parent
    logger.propagate = propagate
    logger.disabled = disabled


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
    original_handlers = request_logger.handlers[:]
    handler = logging.StreamHandler(buf)
    handler.setFormatter(json_logging.JSONRequestLogFormatter())
    try:
        request_logger.handlers = [handler]
        app.test_client().get("/nothing-here")
    finally:
        request_logger.handlers = original_handlers
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


@pytest.mark.parametrize("bad", ["written_ts", u"written_ts", b"written_ts", None, 42, {"written_ts": 1},
                                 ["written_ts", 7], [b"written_ts"], [None]])
def test_invalid_configuration_is_rejected_when_a_formatter_is_built(fresh_json_logging, bad):
    import json_logging
    json_logging.EXCLUDED_FIELDS = bad
    with pytest.raises(TypeError):
        json_logging.JSONLogFormatter()


@pytest.mark.parametrize("good", [["written_ts"], [u"written_ts"], ("written_ts",), {"written_ts"},
                                  frozenset([u"written_ts"])])
def test_valid_configuration_types_are_accepted(fresh_json_logging, good):
    """u"" literals are native str on Python 3; on Python 2 the validator uses basestring so unicode names pass."""
    import json_logging
    json_logging.EXCLUDED_FIELDS = good
    record = logging.LogRecord("n", logging.INFO, __file__, 3, "m", None, None)
    assert "written_ts" not in json.loads(json_logging.JSONLogFormatter().format(record))


def _run_isolated(code):
    """Run code in a fresh interpreter: init_*() changes process-wide state that cannot be fully undone in-process."""
    env = dict(os.environ, PYTHONWARNINGS="ignore")
    env.pop("ENABLE_JSON_LOGGING", None)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")])
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)], cwd=str(ROOT), env=env,
                          capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("init_call", ["init_flask(enable_json=True)", "init_flask(enable_json=False)",
                                       "init_non_web(enable_json=True)"])
def test_invalid_configuration_does_not_poison_a_later_init(init_call):
    result = _run_isolated("""
        import json_logging
        json_logging.EXCLUDED_FIELDS = "written_ts"            # invalid: a bare string
        try:
            json_logging.%(call)s
        except TypeError:
            pass
        else:
            raise AssertionError("invalid EXCLUDED_FIELDS was accepted")
        assert json_logging._current_framework is None and json_logging._request_util is None

        json_logging.EXCLUDED_FIELDS = ["written_ts"]
        json_logging.%(call)s                                   # must not raise "Can not call init more than once"
        if json_logging._current_framework is not None:
            try:
                json_logging.%(call)s
            except RuntimeError as exc:
                assert "Can not call init more than once" in str(exc)
            else:
                raise AssertionError("duplicate initialisation was not rejected")
        print("OK")
    """ % {"call": init_call})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout


def test_invalid_configuration_does_not_leave_request_instrumentation_half_installed():
    result = _run_isolated("""
        import io, json, logging, sys
        import flask
        import json_logging
        json_logging.init_flask(enable_json=True)
        app = flask.Flask("isolated")
        request_logger = logging.getLogger("flask-request-logger")

        json_logging.EXCLUDED_FIELDS = "written_ts"            # invalid, set after a valid init_flask()
        try:
            json_logging.init_request_instrument(app)
        except TypeError:
            pass
        else:
            raise AssertionError("invalid EXCLUDED_FIELDS was accepted")
        assert request_logger.handlers == [] and not app.before_request_funcs and not app.after_request_funcs
        assert logging.getLogger("werkzeug").disabled is False

        json_logging.EXCLUDED_FIELDS = ["written_ts"]
        sys.stdout = buf = io.StringIO()                       # the request logger writes to sys.stdout
        json_logging.init_request_instrument(app)
        app.test_client().get("/missing", headers={"X-Correlation-ID": "retry-1"})
        sys.stdout = sys.__stdout__
        assert len(request_logger.handlers) == 1
        records = [json.loads(line) for line in buf.getvalue().splitlines()]
        assert len(records) == 1 and records[0]["correlation_id"] == "retry-1" and "written_ts" not in records[0]
        print("OK")
    """)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout


def test_exclusion_does_not_mutate_the_log_record(fresh_json_logging):
    import json_logging
    json_logging.EXCLUDED_FIELDS = ["written_ts", "msg"]
    formatter = json_logging.JSONLogFormatter()
    record = logging.LogRecord("n", logging.INFO, __file__, 3, "hello %s", ("x",), None)
    record.props = {"tenant": "acme"}
    before = dict(record.__dict__)
    output = json.loads(formatter.format(record))
    assert "msg" not in output and "written_ts" not in output
    assert record.__dict__ == before
    assert record.getMessage() == "hello x"


def test_exception_formatting_is_removed_only_when_excluded(fresh_json_logging):
    import json_logging
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        exc_info = sys.exc_info()
    record = logging.LogRecord("n", logging.ERROR, __file__, 3, "failed", None, exc_info)

    default = json.loads(json_logging.JSONLogFormatter().format(record))
    assert "ValueError: boom" in default["exc_info"]

    json_logging.EXCLUDED_FIELDS = ["exc_info"]
    excluded = json.loads(json_logging.JSONLogFormatter().format(record))
    assert "exc_info" not in excluded and excluded["msg"] == "failed"


def test_formatters_built_at_different_times_keep_their_own_snapshots(fresh_json_logging):
    import json_logging
    record = logging.LogRecord("n", logging.INFO, __file__, 3, "m", None, None)
    first = json_logging.JSONLogFormatter()
    json_logging.EXCLUDED_FIELDS = ["written_ts"]
    second = json_logging.JSONLogFormatter()
    json_logging.EXCLUDED_FIELDS = ["written_ts", "thread"]
    third = json_logging.JSONLogFormatter()

    assert "written_ts" in json.loads(first.format(record)) and "thread" in json.loads(first.format(record))
    assert "written_ts" not in json.loads(second.format(record)) and "thread" in json.loads(second.format(record))
    assert "written_ts" not in json.loads(third.format(record)) and "thread" not in json.loads(third.format(record))


@pytest.mark.parametrize("excluded, absent", [
    (["written_ts"], {"written_ts"}),                       # the request in issue #98
    ((), set()),                                            # default: nothing removed
    (["correlation_id", "no_such_field"], {"correlation_id"}),  # unknown names are ignored
])
def test_issue_98_handler_added_before_init_flask_gets_the_configured_json_output(fresh_json_logging, excluded,
                                                                                  absent):
    """The setup from issue #98: an application logger already has a StreamHandler when init_flask() runs. The
    library must install its JSON formatter on that handler, with the configured exclusions, without adding one."""
    import flask
    import json_logging
    stream = io.StringIO()
    logger = logging.getLogger("issue-98-app")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stream)
    logger.addHandler(handler)
    assert handler.formatter is None

    json_logging.EXCLUDED_FIELDS = excluded
    app = flask.Flask(__name__)
    json_logging.init_flask(enable_json=True)
    json_logging.init_request_instrument(app, exclude_url_patterns=[r'/health', r'/metrics'])

    @app.route("/work")
    def work():
        logger.info("handled request")
        return json_logging.get_correlation_id()

    response = app.test_client().get("/work", headers={"X-Correlation-ID": "issue-98"})

    assert response.get_data(as_text=True) == "issue-98"     # exclusion changes output only, not the ID lookup
    assert logger.handlers == [handler]
    assert type(handler.formatter) is json_logging.JSONLogWebFormatter
    records = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert len(records) == 1
    record = records[0]
    assert not absent & set(record), record
    expected = {"written_at", "written_ts", "msg", "type", "level", "logger", "correlation_id"} - absent
    assert expected <= set(record), record
    assert record["msg"] == "handled request" and record["level"] == "INFO" and record["type"] == "log"
    if "correlation_id" not in absent:
        assert record["correlation_id"] == "issue-98"
