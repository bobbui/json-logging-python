# coding=utf-8
import logging
import sys

import json_logging
import json_logging.framework
from json_logging import JSONLogWebFormatter
from json_logging.framework_base import BaseAppRequestInstrumentationConfigurator, BaseRequestInfoExtractor, \
    BaseResponseInfoExtractor
from json_logging.util import is_not_match_any_pattern


def is_connexion_present():
    # noinspection PyPep8,PyBroadException
    try:
        import connexion
        return True
    except:
        return False


_AsyncApp = None

if is_connexion_present():
    from connexion import request as request_obj
    import connexion as connexion
    import flask as flask
    from flask import g

    _current_request = request_obj
    _connexion = connexion
    _flask = flask
    _connexion.g = g

    try:
        # Connexion 3+: the ASGI request scope, a werkzeug LocalProxy that is falsy outside a Connexion request
        from connexion.context import scope as _connexion_scope
    except ImportError:
        # Connexion 2: connexion.request is flask.request, so the Flask request context is the only one
        _connexion_scope = None

    try:
        # Connexion 3+: AsyncApp runs without Flask, requests are instrumented by an ASGI middleware instead
        from connexion import AsyncApp as _AsyncApp
        from connexion.middleware import MiddlewarePosition as _MiddlewarePosition
        from contextvars import ContextVar
        from starlette.datastructures import Headers as _Headers
        from starlette.requests import Request as _StarletteRequest

        # The request handled by JSONLoggingConnexionASGIMiddleware, only set while an AsyncApp request is active
        _current_async_request = ContextVar('json_logging_connexion_current_request', default=None)
    except ImportError:
        _AsyncApp = None


class _ASGIResponse(object):
    """Status and headers of an ASGI response, as sent in its ``http.response.start`` message."""

    def __init__(self, message):
        self.status_code = message['status']
        self.headers = _Headers(raw=message.get('headers', []))


class JSONLoggingConnexionASGIMiddleware(object):
    """Logs one request record per HTTP request handled by a Connexion AsyncApp."""

    def __init__(self, app, request_response_dto_class, exclude_url_patterns=tuple()):
        self.app = app
        self.request_response_dto_class = request_response_dto_class
        self.exclude_url_patterns = exclude_url_patterns
        self.request_logger = logging.getLogger('connexion-request-logger')

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        request = _StarletteRequest(scope, receive)
        token = _current_async_request.set(request)
        try:
            # Resolve the correlation id before the handler runs, so the request record and the handler's
            # own records, including those from sync handlers in worker threads, share one id
            try:
                json_logging._request_util.get_correlation_id(request)
            except Exception:
                pass

            if not is_not_match_any_pattern(request.url.path, self.exclude_url_patterns):
                await self.app(scope, receive, send)
                return

            request_response_data = self.request_response_dto_class(request)
            response = None

            async def send_wrapper(message):
                nonlocal response
                if message['type'] == 'http.response.start':
                    response = _ASGIResponse(message)
                await send(message)

            await self.app(scope, receive, send_wrapper)
            if response is not None:
                request_response_data.on_request_complete(response)
                self.request_logger.info("", extra={'request_response_data': request_response_data})
        finally:
            _current_async_request.reset(token)


def _is_async_request(request):
    return _AsyncApp is not None and isinstance(request, _StarletteRequest)


class ConnexionAppRequestInstrumentationConfigurator(BaseAppRequestInstrumentationConfigurator):
    def config(self, app, request_response_dto_class, exclude_url_patterns=[]):
        if not is_connexion_present():
            raise RuntimeError("connexion is not available in system runtime")
        if _AsyncApp is not None and isinstance(app, _AsyncApp):
            # Disable standard access logging, the middleware logs every request
            logging.getLogger('uvicorn.access').disabled = True

            # noinspection PyAttributeOutsideInit
            self.request_logger = logging.getLogger('connexion-request-logger')

            # Added before the ExceptionMiddleware, so error responses produced by exception handlers are logged too
            app.add_middleware(JSONLoggingConnexionASGIMiddleware, position=_MiddlewarePosition.BEFORE_EXCEPTION,
                               request_response_dto_class=request_response_dto_class,
                               exclude_url_patterns=exclude_url_patterns)
            return

        from flask.app import Flask
        if not isinstance(app.app, Flask):
            raise RuntimeError("app is not a valid connexion.app.Connexion app instance")

        # Disable standard logging
        logging.getLogger('werkzeug').disabled = True

        json_logging.util.update_formatter_for_loggers([logging.getLogger('werkzeug')], JSONLogWebFormatter)

        # Connexion wraps a Flask app: unhandled exceptions are reported through its app logger. Flask may attach
        # flask.logging.default_handler to it on first use, so convert that handler and any handler the application
        # already added, without reading app.app.logger (which would attach Flask's handler and duplicate the output).
        if json_logging.ENABLE_JSON_LOGGING:
            from flask.logging import default_handler
            formatter = json_logging._default_formatter or JSONLogWebFormatter
            # Always construct a new formatter: an existing instance may have captured an older EXCLUDED_FIELDS.
            default_handler.setFormatter(formatter())
            json_logging.util.update_formatter_for_loggers([logging.getLogger(app.app.name)], formatter)

        # noinspection PyAttributeOutsideInit
        self.request_logger = logging.getLogger('connexion-request-logger')

        from flask import g

        @app.app.before_request
        def before_request():
            # for connexion 3.0+, requests use starlette
            if hasattr(_current_request, "_starlette_request"):
                path = _current_request.url.path
            else:
                path = _current_request.path
            if is_not_match_any_pattern(path, exclude_url_patterns):
                g.request_response_data = request_response_dto_class(_current_request)

        @app.app.after_request
        def after_request(response):
            if hasattr(g, 'request_response_data'):
                request_response_data = g.request_response_data
                request_response_data.on_request_complete(response)
                self.request_logger.info("", extra={'request_response_data': request_response_data})
            return response


class ConnexionRequestInfoExtractor(BaseRequestInfoExtractor):
    @staticmethod
    def get_request_class_type():
        raise NotImplementedError

    @staticmethod
    def support_global_request_object():
        return True

    @staticmethod
    def get_current_request():
        if _AsyncApp is not None:
            async_request = _current_async_request.get()
            if async_request is not None:
                return async_request
        # The request proxy exists even outside a request; only expose it while a request is active,
        # so callers fall back to json_logging.EMPTY_VALUE instead of generating fabricated IDs.
        if _flask.has_request_context():
            return _current_request
        # Connexion 3 runs error handlers and ASGI middleware outside the Flask request context. The request's
        # correlation header can still be read there, but a generated ID could not be stored (connexion.g is
        # flask.g), so expose the request only when it carries a correlation header.
        if _connexion_scope is not None and _connexion_scope and any(
                header in _current_request.headers for header in json_logging.CORRELATION_ID_HEADERS):
            return _current_request
        return None

    def get_remote_user(self, request):
        if _is_async_request(request):
            # AsyncApp requests carry no parsed authorization, the user is only known to the security handlers
            return json_logging.EMPTY_VALUE
        if request.authorization is not None:
            return request.authorization.username
        else:
            return json_logging.EMPTY_VALUE

    def get_http_header(self, request, header_name, default=None):
        try:
            if header_name in request.headers:
                return request.headers.get(header_name)
        except:
            pass
        return default

    def set_correlation_id(self, request_, value):
        if _is_async_request(request_):
            # request.state lives in the ASGI scope, so every Request built for this scope sees it
            request_.state.correlation_id = value
            return
        try:
            _connexion.g.correlation_id = value
        except:
            pass

    def get_correlation_id_in_request_context(self, request):
        if _is_async_request(request):
            return getattr(request.state, 'correlation_id', None)
        try:
            return _connexion.g.get('correlation_id', None)
        except:
            return None

    def get_protocol(self, request):
        if _is_async_request(request):
            http_version = request.scope.get('http_version')
            return 'HTTP/' + http_version if http_version else json_logging.EMPTY_VALUE
        return request.environ.get('SERVER_PROTOCOL')

    def get_path(self, request):
        if _is_async_request(request):
            return request.url.path
        return request.path

    def get_content_length(self, request):
        if _is_async_request(request):
            return request.headers.get('content-length', json_logging.EMPTY_VALUE)
        return request.content_length

    def get_method(self, request):
        return request.method

    def get_remote_ip(self, request):
        if _is_async_request(request):
            return request.client.host if request.client is not None else json_logging.EMPTY_VALUE
        return request.remote_addr

    def get_remote_port(self, request):
        if _is_async_request(request):
            return request.client.port if request.client is not None else json_logging.EMPTY_VALUE
        return request.environ.get('REMOTE_PORT')


class ConnexionResponseInfoExtractor(BaseResponseInfoExtractor):
    def get_status_code(self, response):
        return response.status_code

    def get_response_size(self, response):
        if isinstance(response, _ASGIResponse):
            return response.headers.get('content-length', json_logging.EMPTY_VALUE)
        return response.calculate_content_length()

    def get_content_type(self, response):
        if isinstance(response, _ASGIResponse):
            return response.headers.get('content-type', json_logging.EMPTY_VALUE)
        return response.content_type
