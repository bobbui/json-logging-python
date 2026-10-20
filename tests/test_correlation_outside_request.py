"""Correlation IDs must not be fabricated outside an active HTTP request (issue #125).

Flask, Quart and Connexion expose a request proxy even when no request is active. These tests
check that background logs get the empty value, that a real request still gets its own ID, and
that no random ID leaks between requests.
"""
import asyncio
import importlib.metadata
import json
import logging

import pytest
from helpers.handler import FormattedMessageCollectorHandler
from helpers.imports import undo_imports_from_package

LOGGER_NAME = "correlation-outside-request-test"


@pytest.fixture(autouse=True)
def restore_framework_logger_state():
    """init_request_instrument() and the Flask/Connexion/Quart integrations change process-wide loggers (handlers,
    parent, disabled). Restore them after each test so no test depends on another test having run."""
    names = ("flask-request-logger", "connexion-request-logger", "quart-request-logger", "werkzeug")
    saved = {}
    for name in names:
        logger = logging.getLogger(name)
        saved[name] = (list(logger.handlers), logger.level, logger.parent, logger.propagate, logger.disabled)
    yield
    for name, (handlers, level, parent, propagate, disabled) in saved.items():
        logger = logging.getLogger(name)
        logger.handlers = handlers
        logger.setLevel(level)
        logger.parent = parent
        logger.propagate = propagate
        logger.disabled = disabled


def _build_app(framework):
    """Return (app, request_context) for a freshly initialised json_logging instance."""
    import json_logging

    if framework == "flask":
        import flask
        app = flask.Flask(__name__)
        json_logging.init_flask(enable_json=True)
        json_logging.init_request_instrument(app)
    elif framework == "connexion":
        import connexion
        app = connexion.FlaskApp(__name__)
        json_logging.init_connexion(enable_json=True)
        json_logging.init_request_instrument(app)
        app = app.app
    else:
        import quart
        app = quart.Quart(__name__)
        json_logging.init_quart(enable_json=True)
        json_logging.init_request_instrument(app)
    return app


def _json_records(handler):
    return [json.loads(message) for message in handler.messages]


@pytest.fixture
def capture():
    """Attach a web-formatted capture handler to a fresh logger, and clean up afterwards."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    handler = FormattedMessageCollectorHandler()
    logger.addHandler(handler)
    yield logger, handler
    logger.removeHandler(handler)
    undo_imports_from_package("json_logging")


@pytest.mark.parametrize("framework", ["flask", "quart", "connexion"])
def test_logs_outside_request_get_empty_correlation_id(capture, framework):
    """Background logs must not receive a fresh UUID per record (the reported bug)."""
    import json_logging
    logger, handler = capture
    app = _build_app(framework)
    handler.setFormatter(json_logging.JSONLogWebFormatter())

    logger.info("startup 1")
    logger.info("startup 2")

    ids = [record["correlation_id"] for record in _json_records(handler)]
    assert ids == [json_logging.EMPTY_VALUE, json_logging.EMPTY_VALUE]
    assert json_logging.get_correlation_id() == json_logging.EMPTY_VALUE
    assert app is not None


def test_flask_background_logs_after_a_request_are_still_empty(capture):
    """Logging after a request completes must not reuse or fabricate the request's ID."""
    import flask
    import json_logging
    logger, handler = capture
    app = _build_app("flask")
    handler.setFormatter(json_logging.JSONLogWebFormatter())

    app.test_client().get("/missing", headers={"X-Correlation-ID": "request-1"})  # 404 is fine
    logger.info("after request")

    assert _json_records(handler)[-1]["correlation_id"] == json_logging.EMPTY_VALUE
    assert flask.has_request_context() is False


@pytest.mark.skipif(importlib.metadata.version("connexion").split(".")[0] != "3",
                    reason="uses the Connexion 3 resolver API; Connexion 2 is covered by the outside-request tests")
def test_supplied_header_is_preserved_inside_connexion_operation(capture, tmp_path):
    """Connexion's request object is only bound while a real operation runs, so use a spec."""
    import json
    import os
    import connexion
    from connexion.resolver import Resolver
    import json_logging
    logger, handler = capture
    spec_dir = str(tmp_path)
    with open(os.path.join(spec_dir, "api.yaml"), "w") as fh:
        fh.write("openapi: 3.0.0\ninfo: {title: t, version: '1'}\npaths:\n  /hi:\n    get:\n"
                 "      operationId: hi\n      responses: {'200': {description: ok}}\n")

    def hi():
        logger.info("in operation")
        return {"correlation_id": json_logging.get_correlation_id()}

    app = connexion.FlaskApp(__name__, specification_dir=spec_dir)
    json_logging.init_connexion(enable_json=True)
    json_logging.init_request_instrument(app)
    app.add_api("api.yaml", resolver=Resolver(lambda operation_id: hi))
    handler.setFormatter(json_logging.JSONLogWebFormatter())

    response = app.test_client().get("/hi", headers={"X-Correlation-ID": "given-1"})
    assert response.status_code == 200
    assert json.loads(response.text)["correlation_id"] == "given-1"
    assert _json_records(handler)[-1]["correlation_id"] == "given-1"


@pytest.mark.parametrize("framework", ["flask", "quart"])
def test_supplied_header_is_preserved_inside_request(capture, framework):
    import json_logging
    logger, handler = capture
    app = _build_app(framework)
    handler.setFormatter(json_logging.JSONLogWebFormatter())

    if framework == "quart":
        async def run():
            async with app.test_request_context("/", headers={"X-Correlation-ID": "given-1"}):
                logger.info("in request")
                return json_logging.get_correlation_id()
        assert asyncio.run(run()) == "given-1"
    else:
        with app.test_request_context("/", headers={"X-Correlation-ID": "given-1"}):
            logger.info("in request")
            assert json_logging.get_correlation_id() == "given-1"

    assert _json_records(handler)[-1]["correlation_id"] == "given-1"


def test_generated_id_is_stable_inside_one_request_and_not_reused_afterwards(capture):
    import json_logging
    logger, handler = capture
    app = _build_app("flask")
    handler.setFormatter(json_logging.JSONLogWebFormatter())

    with app.test_request_context("/"):
        logger.info("first in request")
        logger.info("second in request")
        generated = json_logging.get_correlation_id()
    logger.info("after request")

    ids = [record["correlation_id"] for record in _json_records(handler)]
    assert generated not in (json_logging.EMPTY_VALUE, None)
    assert ids[0] == generated and ids[1] == generated
    assert ids[2] == json_logging.EMPTY_VALUE


def test_concurrent_flask_requests_do_not_exchange_ids(capture):
    from concurrent.futures import ThreadPoolExecutor
    import json_logging
    logger, handler = capture
    app = _build_app("flask")
    handler.setFormatter(json_logging.JSONLogWebFormatter())
    client = app.test_client()

    @app.route("/echo")
    def echo():
        return json_logging.get_correlation_id()

    ids = ["parallel-%d" % index for index in range(8)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda cid: client.get("/echo", headers={"X-Correlation-ID": cid}).get_data(as_text=True), ids))

    assert results == ids
    assert json_logging.get_correlation_id() == json_logging.EMPTY_VALUE
