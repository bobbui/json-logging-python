import logging
import sys

import json_logging
import json_logging.framework
from json_logging.framework_base import BaseAppRequestInstrumentationConfigurator, BaseRequestInfoExtractor, \
    BaseResponseInfoExtractor

from json_logging.util import is_not_match_any_pattern

import fastapi
import starlette.requests
import starlette.responses

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

_request_config_class = None
# Only enabled on the Python versions covered by CI (3.9+). On older versions, including 3.6 where at
# most the thread-local `contextvars` backport exists, the previous call-stack lookup is kept unchanged.
if sys.version_info >= (3, 9):
    from contextvars import ContextVar
    _current_request = ContextVar('json_logging_fastapi_current_request', default=None)
else:  # pragma: no cover
    _current_request = None


class JSONLoggingASGIMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, exclude_url_patterns=tuple()) -> None:
        super().__init__(app)
        self.request_logger = logging.getLogger('fastapi-request-logger')
        self.exclude_url_patterns = exclude_url_patterns
        logging.getLogger("uvicorn.access").propagate = False

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Run request instrumentation with a context shared by downstream work.

        On Python 3.9+, resolve the correlation ID before workers run and
        restore the previous request context when processing completes.
        """
        # The current request must also be visible in FastAPI's sync worker threads.
        # Context is propagated by AnyIO, unlike Python call-stack frame locals.
        token = _current_request.set(request) if _current_request is not None else None
        try:
            # Resolve (and if needed create) the correlation id once per request, before handlers
            # run, so concurrent worker threads of one request read the same id instead of each
            # creating their own. Failures are left to the later lazy lookups, as before. Only
            # done when the request context is in use; otherwise the previous behaviour is kept.
            if token is not None:
                try:
                    json_logging._request_util.get_correlation_id(request)
                except Exception:
                    pass
            log_request = is_not_match_any_pattern(request.url.path, self.exclude_url_patterns)

            if not log_request:
                return await call_next(request)

            request_response_data = _request_config_class(request)
            response = await call_next(request)
            request_response_data.on_request_complete(response)
            self.request_logger.info(
                "", extra={"request_response_data": request_response_data, "type": "request"}
            )
            return response
        finally:
            if token is not None:
                _current_request.reset(token)


class FastAPIAppRequestInstrumentationConfigurator(BaseAppRequestInstrumentationConfigurator):
    def config(self, app, request_response_dto_class, exclude_url_patterns=[]):
        if not isinstance(app, fastapi.FastAPI):
            raise RuntimeError("app is not a valid fastapi.FastAPI instance")

        global _request_config_class
        _request_config_class = request_response_dto_class

        # Disable standard logging
        logging.getLogger('uvicorn.access').disabled = True

        # noinspection PyAttributeOutsideInit
        self.request_logger = logging.getLogger('fastapi-request-logger')

        app.add_middleware(JSONLoggingASGIMiddleware, exclude_url_patterns=exclude_url_patterns)


class FastAPIRequestInfoExtractor(BaseRequestInfoExtractor):
    @staticmethod
    def get_request_class_type():
        return starlette.requests.Request

    @staticmethod
    def support_global_request_object():
        return _current_request is not None

    @staticmethod
    def get_current_request():
        """Return the active request, falling back to call-stack discovery.

        The fallback preserves request lookup when middleware context is absent.
        """
        request = _current_request.get()
        if request is None:
            # Outside JSONLoggingASGIMiddleware (e.g. init_request_instrument() was not
            # called) keep the previous call-stack discovery.
            request = json_logging._request_util.get_request_from_call_stack()
        return request

    def get_remote_user(self, request: starlette.requests.Request):
        try:
            return request.user
        except AssertionError:
            return json_logging.EMPTY_VALUE

    def get_http_header(self, request: starlette.requests.Request, header_name, default=None):
        try:
            if header_name in request.headers:
                return request.headers.get(header_name)
        except:
            pass
        return default

    def set_correlation_id(self, request_, value):
        request_.state.correlation_id = value

    def get_correlation_id_in_request_context(self, request: starlette.requests.Request):
        try:
            return request.state.correlation_id
        except AttributeError:
            return None

    def get_protocol(self, request: starlette.requests.Request):
        protocol = str(request.scope.get('type', ''))
        http_version = str(request.scope.get('http_version', ''))
        if protocol.lower() == 'http' and http_version:
            return protocol.upper() + "/" + http_version
        return json_logging.EMPTY_VALUE

    def get_path(self, request: starlette.requests.Request):
        return request.url.path

    def get_content_length(self, request: starlette.requests.Request):
        return request.headers.get('content-length', json_logging.EMPTY_VALUE)

    def get_method(self, request: starlette.requests.Request):
        return request.method

    def get_remote_ip(self, request: starlette.requests.Request):
        if request.client is not None:
            return request.client.host
        return json_logging.EMPTY_VALUE

    def get_remote_port(self, request: starlette.requests.Request):
        if request.client is not None:
            return request.client.port
        return json_logging.EMPTY_VALUE


class FastAPIResponseInfoExtractor(BaseResponseInfoExtractor):
    def get_status_code(self, response: starlette.responses.Response):
        return response.status_code

    def get_response_size(self, response: starlette.responses.Response):
        return response.headers.get('content-length', json_logging.EMPTY_VALUE)

    def get_content_type(self, response: starlette.responses.Response):
        return response.headers.get('content-type', json_logging.EMPTY_VALUE)
