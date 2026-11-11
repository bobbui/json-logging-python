# coding=utf-8
# Connexion 3 AsyncApp support. Kept out of the package __init__ because it uses async syntax, and that module is
# imported on every "import json_logging". This one is only imported when Connexion 3 is installed.
import logging
from contextvars import ContextVar

from starlette.datastructures import Headers
from starlette.requests import Request

import json_logging
from json_logging.util import is_not_match_any_pattern

# The request handled by JSONLoggingConnexionASGIMiddleware, only set while an AsyncApp request is active
current_async_request = ContextVar('json_logging_connexion_current_request', default=None)


class ASGIResponse(object):
    """Status and headers of an ASGI response, as sent in its ``http.response.start`` message."""

    def __init__(self, message):
        self.status_code = message['status']
        self.headers = Headers(raw=message.get('headers', []))


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

        request = Request(scope, receive)
        token = current_async_request.set(request)
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
                    response = ASGIResponse(message)
                await send(message)

            await self.app(scope, receive, send_wrapper)
            if response is not None:
                request_response_data.on_request_complete(response)
                self.request_logger.info("", extra={'request_response_data': request_response_data})
        finally:
            current_async_request.reset(token)
