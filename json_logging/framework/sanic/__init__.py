# coding=utf-8
import logging
import sys

import json_logging
import json_logging.framework
from json_logging.framework_base import FrameworkConfigurator, AppRequestInstrumentationConfigurator, RequestAdapter, \
    ResponseAdapter


def is_sanic_present():
    # noinspection PyBroadException
    try:
        # noinspection PyPackageRequirements
        from sanic import Sanic
        return True
    except:
        return False


class SanicAppConfigurator(FrameworkConfigurator):

    def config(self):
        if not is_sanic_present():
            raise RuntimeError("Sanic is not available in system runtime")

        # from sanic.config import LOGGING
        # noinspection PyPackageRequirements
        from sanic.log import LOGGING_CONFIG_DEFAULTS as LOGGING

        LOGGING['disable_existing_loggers'] = False
        LOGGING['formatters']['generic']['class'] = "json_logging.JSONLogFormatter"
        del LOGGING['formatters']['generic']['format']

        LOGGING['formatters']['access']['class'] = "json_logging.JSONLogFormatter"
        del LOGGING['formatters']['access']['format']


class SanicAppRequestInstrumentationConfigurator(AppRequestInstrumentationConfigurator):
    def config(self, app):
        if not is_sanic_present():
            raise RuntimeError("Sanic is not available in system runtime")
        # noinspection PyPackageRequirements
        from sanic import Sanic
        if not isinstance(app, Sanic):
            raise RuntimeError("app is not a valid Sanic.app.Sanic app instance")

        # noinspection PyAttributeOutsideInit
        self.request_logger = logging.getLogger('sanic-request')
        self.request_logger.setLevel(logging.DEBUG)
        self.request_logger.addHandler(logging.StreamHandler(sys.stdout))

        @app.middleware('request')
        def before_request(request):
            request['request_info'] = json_logging.RequestInfo(request)

        @app.middleware('response')
        def after_request(request, response):
            request_info = request['request_info']
            request_info.update_response_status(response)
            self.request_logger.info("", extra={'request_info': request_info, 'type': 'request'})

    def get_request_logger(self):
        return self.request_logger


class SanicRequestAdapter(RequestAdapter):

    @staticmethod
    def get_current_request():
        raise NotImplementedError

    def is_in_request_context(self, request):
        return request is not None

    @staticmethod
    def support_global_request_object():
        return False

    # noinspection PyPackageRequirements
    @staticmethod
    def get_request_class_type():
        from sanic.request import Request
        return Request

    def get_remote_user(self, request):
        # todo: implement it
        return None

    def get_http_header(self, request, header_name, default=None):
        if header_name in request.headers:
            return request.headers.get(header_name)
        return default

    def set_correlation_id(self, request_, value):
        request_['correlation_id'] = value

    def get_correlation_id_in_request_context(self, request):
        return request.get('correlation_id')

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


class SanicResponseAdapter(ResponseAdapter):

    def get_status_code(self, response):
        return response.status

    def get_response_size(self, response):
        return json_logging.EMPTY_VALUE

    def get_content_type(self, response):
        return response.content_type
