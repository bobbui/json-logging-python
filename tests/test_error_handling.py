"""Error-path formatting: an exception must reach the log as one JSON record.

Regression coverage for the 2026-11-02 API incident: unhandled exceptions reported by the
Flask/connexion app logger were emitted as plain multi-line text, so they never carried a
``level`` or a single ``exc_info`` field and could not be alerted on.

The toolchain was running ``logging.basicConfig()`` before ``json_logging.init_*()``. That call
installs a root handler whose formatter is an explicit ``logging.Formatter`` (default format
``%(levelname)s:%(name)s:%(message)s``); the handler is therefore not covered by
``logging._defaultFormatter`` and, before the fix, the root logger was not part of the formatter
sweep either. Every record propagating to root, including Flask's exception log, stayed plain.
"""
import io
import json
import logging

import pytest

from helpers.imports import undo_imports_from_package

EXCEPTION_MESSAGE = "'NoneType' object is not iterable"
LOGGER_NAME = "user_db_api.app"
REQUEST_LOGGER_NAMES = ["flask-request-logger", "connexion-request-logger"]


@pytest.fixture
def fresh_json_logging():
    """Import a pristine json_logging so module level init state does not leak between tests."""
    undo_imports_from_package("json_logging")
    import json_logging
    yield json_logging
    undo_imports_from_package("json_logging")


def _loggers_to_restore():
    """The root logger, every logger that exists now, and the shared loggers these tests create."""
    shared_names = [LOGGER_NAME, __name__] + REQUEST_LOGGER_NAMES
    loggers = [logging.root] + [logging.getLogger(name) for name in shared_names]
    loggers.extend(entry for entry in logging.Logger.manager.loggerDict.values() if isinstance(entry, logging.Logger))
    unique_loggers = []
    seen = set()
    for logger in loggers:
        if id(logger) not in seen:
            seen.add(id(logger))
            unique_loggers.append(logger)
    return unique_loggers


@pytest.fixture(autouse=True)
def restore_process_logging():
    """Undo the process-global logging changes these tests deliberately make."""
    import flask.logging as flask_logging

    # init_*() rewrites the formatter of every handler it finds, and init_request_instrument() adds an output
    # handler to a shared request logger, so snapshot each handler list and each handler's formatter.
    saved_loggers = [
        (logger, logger.handlers[:], [(handler, handler.formatter) for handler in logger.handlers])
        for logger in _loggers_to_restore()
    ]
    saved_root_level = logging.root.level
    saved_default_formatter = logging._defaultFormatter
    saved_flask_default_formatter = flask_logging.default_handler.formatter
    saved_flask_default_stream = flask_logging.default_handler.stream
    yield
    for logger, handlers, handler_formatters in saved_loggers:
        logger.handlers[:] = handlers
        for handler, formatter in handler_formatters:
            handler.setFormatter(formatter)
    logging.root.setLevel(saved_root_level)
    logging._defaultFormatter = saved_default_formatter
    flask_logging.default_handler.setFormatter(saved_flask_default_formatter)
    flask_logging.default_handler.stream = saved_flask_default_stream


def raise_type_error():
    """Raise the exception type that the production incident logged."""
    raise TypeError(EXCEPTION_MESSAGE)


def configure_root_logger_like_basic_config():
    """Reproduce the toolchain setup: a root handler with an explicit default Formatter, and return the handler."""
    remove_root_handlers()
    logging.root.setLevel(logging.INFO)
    logging.basicConfig()
    handler = logging.root.handlers[0]
    assert type(handler.formatter) is logging.Formatter, "basicConfig() must install an explicit Formatter"
    return handler


def capture_stream(handler):
    """Point *handler* at a fresh buffer, so only records emitted afterwards are captured."""
    buffer = io.StringIO()
    handler.stream = buffer
    return buffer


def remove_root_handlers():
    """Leave the root logger without handlers, as a gunicorn-hosted worker does."""
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)


def parse_records(text):
    """Parse every non-empty line as JSON, so a plain text line fails the test instead of being skipped."""
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def error_records(text):
    """The ERROR log records in *text*, which must contain JSON lines only."""
    return [
        record
        for record in parse_records(text)
        if record.get("type") == "log" and record.get("level") == "ERROR"
    ]


def assert_single_exception_record(records, message, logger_name=LOGGER_NAME):
    """Assert that exactly one exception record carried the message and the traceback."""
    assert len(records) == 1, [record.get("msg") for record in records]
    record = records[0]
    assert record["logger"] == logger_name
    assert record["msg"] == message
    assert "Traceback (most recent call last)" in record["exc_info"]
    assert EXCEPTION_MESSAGE in record["exc_info"]


def test_exception_through_root_handler_configured_before_init_is_one_json_record(fresh_json_logging):
    """A root handler with an explicit formatter is converted by init_{non_web}."""
    handler = configure_root_logger_like_basic_config()

    fresh_json_logging.init_non_web(enable_json=True)
    buffer = capture_stream(handler)

    try:
        raise_type_error()
    except TypeError:
        logging.getLogger(LOGGER_NAME).error("Exception on /v1/user_resource_access_info [GET]", exc_info=True)

    assert_single_exception_record(error_records(buffer.getvalue()), "Exception on /v1/user_resource_access_info [GET]")


def test_flask_unhandled_exception_with_root_handler_is_one_json_record(fresh_json_logging):
    """An unhandled Flask exception propagated to a configured root handler is one JSON record."""
    import flask

    handler = configure_root_logger_like_basic_config()
    fresh_json_logging.init_flask(enable_json=True)
    app = flask.Flask(LOGGER_NAME)
    fresh_json_logging.init_request_instrument(app)
    buffer = capture_stream(handler)

    @app.route("/boom")
    def boom():
        raise_type_error()

    assert app.test_client().get("/boom").status_code == 500

    assert_single_exception_record(error_records(buffer.getvalue()), "Exception on /boom [GET]")


def test_flask_app_logger_handler_added_before_instrumentation_is_one_json_record(fresh_json_logging):
    """A handler Flask attached to the app logger before instrumentation is converted."""
    import flask

    remove_root_handlers()
    fresh_json_logging.init_flask(enable_json=True)
    app = flask.Flask(LOGGER_NAME)
    app.logger  # the application used its logger before instrumentation, so Flask has attached its own handler
    assert app.logger.handlers, "expected Flask to attach its own handler"
    fresh_json_logging.init_request_instrument(app)

    buffer = io.StringIO()
    app.logger.handlers[0].stream = buffer

    @app.route("/boom")
    def boom():
        raise_type_error()

    assert app.test_client().get("/boom").status_code == 500

    assert_single_exception_record(error_records(buffer.getvalue()), "Exception on /boom [GET]")


def test_flask_handler_attached_on_first_use_is_json(fresh_json_logging, capfd):
    """The handler Flask attaches on first use is JSON, and json_logging adds no handler of its own."""
    import flask

    remove_root_handlers()
    fresh_json_logging.init_flask(enable_json=True)
    app = flask.Flask(LOGGER_NAME)
    fresh_json_logging.init_request_instrument(app)

    # json_logging must not attach a handler of its own: Flask attaches flask.logging.default_handler on first use.
    assert logging.getLogger(LOGGER_NAME).handlers == []

    @app.route("/boom")
    def boom():
        raise_type_error()

    assert app.test_client().get("/boom").status_code == 500

    assert app.logger.handlers, "expected Flask to attach its own handler on first use"
    assert_single_exception_record(error_records(capfd.readouterr().err), "Exception on /boom [GET]")


def test_flask_app_logger_is_left_plain_when_json_logging_is_disabled(fresh_json_logging):
    """With JSON logging disabled the app logger keeps its plain text formatter."""
    import flask
    from flask.logging import default_handler

    remove_root_handlers()
    plain_formatter = logging.Formatter("%(levelname)s in app: %(message)s")
    default_handler.setFormatter(plain_formatter)
    fresh_json_logging.init_flask()  # enable_json defaults to False
    app = flask.Flask(LOGGER_NAME)
    app.logger  # Flask attaches its own handler, with a plain text formatter
    assert app.logger.handlers

    fresh_json_logging.init_request_instrument(app)

    assert default_handler.formatter is plain_formatter, "JSON is disabled, the formatter must not change"
    assert app.logger.handlers[0].formatter is plain_formatter


def test_connexion_unhandled_request_exception_is_one_json_record(fresh_json_logging):
    """A failing Connexion 3 request, through its real middleware, logs one JSON exception record."""
    connexion = pytest.importorskip("connexion")

    handler = configure_root_logger_like_basic_config()
    fresh_json_logging.init_connexion(enable_json=True)
    app = connexion.FlaskApp(__name__, specification_dir=".")
    app.add_api({
        "openapi": "3.0.0",
        "info": {"title": "exception logging", "version": "1"},
        "paths": {"/boom": {"get": {"operationId": f"{__name__}.boom", "responses": {"200": {"description": "ok"}}}}},
    })
    fresh_json_logging.init_request_instrument(app)
    buffer = capture_stream(handler)

    assert app.test_client().get("/boom").status_code == 500

    # Connexion 3 reports the failure through its own middleware logger, which propagates to the converted root handler.
    assert_single_exception_record(
        error_records(buffer.getvalue()), f"TypeError({EXCEPTION_MESSAGE!r})", "connexion.middleware.exceptions")


def test_connexion_app_logger_exception_is_one_json_record(fresh_json_logging):
    """The app logger of a Connexion application is converted, which Connexion 2 and app code rely on."""
    connexion = pytest.importorskip("connexion")

    remove_root_handlers()
    fresh_json_logging.init_connexion(enable_json=True)
    app = connexion.FlaskApp(__name__, specification_dir=".")
    app.app.logger  # the application used its logger before instrumentation
    fresh_json_logging.init_request_instrument(app)

    logger = app.app.logger
    assert logger.handlers, "expected Flask to attach its own handler"
    buffer = io.StringIO()
    logger.handlers[0].stream = buffer

    try:
        raise_type_error()
    except TypeError:
        logger.error("Exception on /v1/user_resource_access_info [GET]", exc_info=True)

    assert_single_exception_record(
        error_records(buffer.getvalue()), "Exception on /v1/user_resource_access_info [GET]", logger.name)


def boom():
    """Operation used by the Connexion specification above; it fails the way production did."""
    raise_type_error()
