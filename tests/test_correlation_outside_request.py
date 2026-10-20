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
    """Start from a fresh json_logging import, attach a web-formatted capture handler to a test logger, and clean up
    both afterwards. Requested after the autouse logger-state fixture, so it is torn down first."""
    undo_imports_from_package("json_logging")
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


IS_CONNEXION_3 = importlib.metadata.version("connexion").split(".")[0] == "3"


def _connexion3_app(tmp_path, logger, view, after_middleware_hook=None):
    """A Connexion 3 FlaskApp with code paths that run outside the Flask request context: an error handler
    (Connexion's ExceptionMiddleware) and an ASGI middleware that logs after the app has returned."""
    import connexion
    from connexion.resolver import Resolver
    import json_logging
    (tmp_path / "api.yaml").write_text(
        "openapi: 3.0.0\ninfo: {title: t, version: '1'}\npaths:\n  /op:\n    get:\n      operationId: op\n"
        "      parameters: [{name: n, in: query, schema: {type: integer}}]\n"
        "      responses: {'200': {description: ok}}\n")

    class AfterAppMiddleware:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)
            if scope["type"] == "http":
                if after_middleware_hook is not None:
                    await after_middleware_hook()
                logger.info("middleware after app", extra={"props": {"query": scope["query_string"].decode()}})

    def on_error(request, exc):
        logger.info("error handler", extra={"props": {"query": request.url.query}})
        logger.info("error handler again", extra={"props": {"query": request.url.query}})
        return connexion.lifecycle.ConnexionResponse(status_code=500, body=b"handled")

    app = connexion.FlaskApp(__name__, specification_dir=str(tmp_path))
    json_logging.init_connexion(enable_json=True)
    # Request logging is excluded: Connexion 3 request records fail independently of this test (issue #101).
    json_logging.init_request_instrument(app, exclude_url_patterns=[r"^/op$"])
    app.add_error_handler(ValueError, on_error)
    app.add_middleware(AfterAppMiddleware)
    app.add_api("api.yaml", resolver=Resolver(lambda operation_id: view))
    return app


@pytest.mark.skipif(not IS_CONNEXION_3, reason="Connexion 3 runs error handlers and middleware outside Flask")
def test_connexion3_header_is_preserved_outside_the_flask_request_context(capture, tmp_path):
    """Connexion 3 error handlers and ASGI middleware have a Connexion request but no Flask request context."""
    import flask
    import json_logging
    logger, handler = capture
    flask_context_in_handler = []

    def view(n=None):
        logger.info("view")
        if n == 1:
            flask_context_in_handler.append(flask.has_request_context())
            raise ValueError("handled by the Connexion error handler")
        return {"correlation_id": json_logging.get_correlation_id()}

    app = _connexion3_app(tmp_path, logger, view)
    handler.setFormatter(json_logging.JSONLogWebFormatter())
    client = app.test_client()

    assert client.get("/op", headers={"X-Correlation-ID": "test-123"}).status_code == 200
    assert client.get("/op?n=1", headers={"X-Request-ID": "test-456"}).status_code == 500

    records = [(r["msg"], r["correlation_id"]) for r in _json_records(handler)]
    assert records == [
        ("view", "test-123"), ("middleware after app", "test-123"),
        # the view raised, so the exception propagated through the middleware before its post-app log
        ("view", "test-456"), ("error handler", "test-456"), ("error handler again", "test-456"),
    ]
    assert flask_context_in_handler == [True]    # the view runs in Flask; the handler and middleware do not
    logger.info("after requests")
    assert _json_records(handler)[-1]["correlation_id"] == json_logging.EMPTY_VALUE
    assert json_logging.get_correlation_id() == json_logging.EMPTY_VALUE


@pytest.mark.skipif(not IS_CONNEXION_3, reason="Connexion 3 runs error handlers and middleware outside Flask")
def test_connexion3_without_header_does_not_fabricate_ids_outside_the_flask_request_context(capture, tmp_path):
    """A generated ID lives in flask.g, which is gone once Connexion's middleware runs. Logs there must get '-'
    rather than a fresh UUID per record; logs inside the view keep one generated ID."""
    import json_logging
    logger, handler = capture

    def view(n=None):
        logger.info("view 1", extra={"props": {"n": n}})
        logger.info("view 2", extra={"props": {"n": n}})
        if n == 1:
            raise ValueError("handled by the Connexion error handler")
        return {"correlation_id": json_logging.get_correlation_id()}

    app = _connexion3_app(tmp_path, logger, view)
    handler.setFormatter(json_logging.JSONLogWebFormatter())
    client = app.test_client()
    returned = client.get("/op?n=0").json()["correlation_id"]
    assert client.get("/op?n=1").status_code == 500

    ids = [(r["msg"], r.get("n"), r["correlation_id"]) for r in _json_records(handler)]
    (_, _, first), (_, _, second), middleware, (_, _, third), (_, _, fourth), handler_1, handler_2 = ids
    assert first == second == returned and returned != json_logging.EMPTY_VALUE   # one ID within a request
    assert third == fourth and third not in (returned, json_logging.EMPTY_VALUE)  # a new ID for the next request
    assert middleware == ("middleware after app", None, json_logging.EMPTY_VALUE)
    assert handler_1 == ("error handler", None, json_logging.EMPTY_VALUE)
    assert handler_2 == ("error handler again", None, json_logging.EMPTY_VALUE)


@pytest.mark.skipif(not IS_CONNEXION_3, reason="Connexion 3 runs error handlers and middleware outside Flask")
def test_connexion3_concurrent_requests_do_not_exchange_ids(capture, tmp_path):
    """Requests run as concurrent ASGI tasks. The middleware waits until every request has finished its view
    before logging, so the Connexion contexts of all requests are live at the same time."""
    import httpx
    import json_logging
    logger, handler = capture
    count = 5
    finished_views = []
    state = {}      # the Event is created inside the running loop (required on Python 3.9)

    async def wait_for_all_views():
        finished_views.append(1)
        if len(finished_views) == count:
            state["all_views_done"].set()
        await asyncio.wait_for(state["all_views_done"].wait(), timeout=10)

    def view(n=None):
        logger.info("view", extra={"props": {"query": "n=%d" % n}})
        return {"correlation_id": json_logging.get_correlation_id()}

    app = _connexion3_app(tmp_path, logger, view, after_middleware_hook=wait_for_all_views)
    handler.setFormatter(json_logging.JSONLogWebFormatter())

    async def run():
        state["all_views_done"] = asyncio.Event()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await asyncio.gather(*[client.get("/op?n=%d" % n, headers={"X-Correlation-ID": "cx-%d" % n})
                                          for n in range(count)])

    responses = asyncio.run(run())
    assert [r.json()["correlation_id"] for r in responses] == ["cx-%d" % n for n in range(count)]
    records = _json_records(handler)
    assert len(records) == 2 * count
    for record in records:
        assert record["correlation_id"] == "cx-" + record["query"].split("=")[1], record
    assert json_logging.get_correlation_id() == json_logging.EMPTY_VALUE


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


def test_concurrent_flask_requests_keep_their_own_generated_ids(capture):
    """Requests without a correlation header each generate an ID. All requests are held in flight together by a
    barrier between two log calls, so an ID stored outside the request context would be picked up by another
    request's second log record."""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    import flask
    import json_logging
    logger, handler = capture
    app = _build_app("flask")
    handler.setFormatter(json_logging.JSONLogWebFormatter())
    count = 6
    barrier = threading.Barrier(count, timeout=10)

    @app.route("/work/<int:request_number>")
    def work(request_number):
        logger.info("before barrier", extra={"props": {"request_number": request_number}})
        barrier.wait()      # every request has generated its ID before any request logs again
        logger.info("after barrier", extra={"props": {"request_number": request_number}})
        return json_logging.get_correlation_id()

    def call(request_number):
        with app.test_client() as client:   # one client per thread: no shared client state
            return client.get("/work/%d" % request_number).get_data(as_text=True)

    with ThreadPoolExecutor(max_workers=count) as pool:
        returned = dict(zip(range(count), pool.map(call, range(count))))
    logger.info("after all requests")

    assert all(cid not in ("", json_logging.EMPTY_VALUE) for cid in returned.values()), returned
    assert len(set(returned.values())) == count, returned
    records = _json_records(handler)
    in_request = [r for r in records if "request_number" in r]
    assert len(in_request) == 2 * count
    for record in in_request:
        assert record["correlation_id"] == returned[record["request_number"]], record
    assert records[-1]["msg"] == "after all requests"
    assert records[-1]["correlation_id"] == json_logging.EMPTY_VALUE
    assert flask.has_request_context() is False
