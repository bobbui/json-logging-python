# coding=utf-8
import json_logging
import json_logging.framework
from json_logging.framework_base import AppRequestInstrumentationConfigurator, RequestAdapter, ResponseAdapter
import logging
from json_logging.util import is_not_match_any_pattern
from http.client import HTTPMessage
from http.server import HTTPServer
from typing import AnyStr


class PlainHTTPResponse:
    # default is Unknown Request
    status = 500
    content_type = 'text/plain'
    content = b'Unknown Request'
    request_info = None


class PlainHTTPAppRequestInstrumentationConfigurator(AppRequestInstrumentationConfigurator):
    def config(self, app: HTTPServer, exclude_url_patterns=[]):
        if not isinstance(app, HTTPServer):
            raise RuntimeError("app is not a valid HTTPServer app instance")
        self.request_logger = logging.getLogger('plain-http-request-logger')

        def attach_req_info_to_response(response: PlainHTTPResponse, path: AnyStr, request, headers: HTTPMessage):
            if is_not_match_any_pattern(path, exclude_url_patterns):
                response.request_info = json_logging.RequestInfo(request)
                response.request_info.headers = headers
        app.attach_req_info_to_response = attach_req_info_to_response

        def after_request(response: PlainHTTPResponse):
            if response.request_info:
                request_info = response.request_info
                request_info.update_response_status(response)

                self.request_logger.info("", extra={'request_info': request_info})
            return response
        app.after_request = after_request

    def get_request_logger(self):
        return self.request_logger


class PlainHTTPRequestAdapter(RequestAdapter):

    @staticmethod
    def get_current_request():
        # needed inf support_global_request_object==true
        raise NotImplementedError

    @staticmethod
    def support_global_request_object():
        return False

    # noinspection PyPackageRequirements
    @staticmethod
    def get_request_class_type():
        return PlainHTTPResponse

    def get_remote_user(self, request):
        # todo: implement it
        return None

    def get_http_header(self, request: PlainHTTPResponse, header_name, default=None):
        headers = request.request_info.headers
        if header_name in headers:
            return headers.get(header_name)
        return default

    def set_correlation_id(self, request, value):
        request.ctx.correlation_id = value

    def get_correlation_id_in_request_context(self, request):
        try:
            return request.ctx.correlation_id
        except AttributeError:
            return None

    def get_protocol(self, request):
        return json_logging.EMPTY_VALUE

    def get_path(self, request):
        return request.path

    def get_content_length(self, request):
        return json_logging.EMPTY_VALUE

    def get_method(self, request):
        return request.method

    def get_remote_ip(self, request):
        return request.ip[0]

    def get_remote_port(self, request):
        return json_logging.EMPTY_VALUE


class PlainHTTPResponseAdapter(ResponseAdapter):

    def get_status_code(self, response: PlainHTTPResponse):
        return response.status

    def get_response_size(self, response: PlainHTTPResponse):
        return len(response.content)

    def get_content_type(self, response: PlainHTTPResponse):
        return response.content_type
