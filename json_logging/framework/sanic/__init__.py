# coding=utf-8
import logging
import logging.config

import sys

import json_logging
import json_logging.framework
from json_logging.framework_base import (
    BaseFrameworkConfigurator,
    BaseAppRequestInstrumentationConfigurator,
    BaseRequestInfoExtractor,
    BaseResponseInfoExtractor,
)
from json_logging.util import is_not_match_any_pattern


def is_sanic_present():
    # noinspection PyBroadException
    try:
        # noinspection PyPackageRequirements
        from sanic import Sanic

        return True
    except:
        return False


class SanicAppConfigurator(BaseFrameworkConfigurator):
    def config(self):
        if not is_sanic_present():
            raise RuntimeError("Sanic is not available in system runtime")

        # from sanic.config import LOGGING
        # noinspection PyPackageRequirements
        from sanic.log import LOGGING_CONFIG_DEFAULTS

        LOGGING_CONFIG_DEFAULTS["disable_existing_loggers"] = False
        LOGGING_CONFIG_DEFAULTS["formatters"]["generic"][
            "class"
        ] = "json_logging.JSONLogFormatter"
        del LOGGING_CONFIG_DEFAULTS["formatters"]["generic"]["format"]

        LOGGING_CONFIG_DEFAULTS["formatters"]["access"][
            "class"
        ] = "json_logging.JSONLogFormatter"
        del LOGGING_CONFIG_DEFAULTS["formatters"]["access"]["format"]

        # logging.config.dictConfig(LOGGING_CONFIG_DEFAULTS)


class SanicAppRequestInstrumentationConfigurator(BaseAppRequestInstrumentationConfigurator):
    def config(self, app, request_response_dto_class, exclude_url_patterns=[]):
        if not is_sanic_present():
            raise RuntimeError("Sanic is not available in system runtime")
        # noinspection PyPackageRequirements
        from sanic import Sanic

        if not isinstance(app, Sanic):
            raise RuntimeError("app is not a valid Sanic.app.Sanic app instance")

        # noinspection PyAttributeOutsideInit
        self.request_logger = logging.getLogger("sanic-request")

        logging.getLogger("sanic.access").disabled = True

        @app.middleware("request")
        def before_request(request):
            if is_not_match_any_pattern(request.path, exclude_url_patterns):
                request.ctx.request_response_data = request_response_dto_class(request)

        @app.middleware("response")
        def after_request(request, response):
            if hasattr(request.ctx, "request_response_data"):
                request_response_data = request.ctx.request_response_data
                request_response_data.on_request_complete(response)
                self.request_logger.info(
                    "", extra={"request_response_data": request_response_data, "type": "request"}
                )


class SanicRequestInfoExtractor(BaseRequestInfoExtractor):
    @staticmethod
    def get_current_request():
        raise NotImplementedError

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
        return request.ip

    def get_remote_port(self, request):
        return json_logging.EMPTY_VALUE


class SanicResponseInfoExtractor(BaseResponseInfoExtractor):
    def get_status_code(self, response):
        return response.status

    def get_response_size(self, response):
        return json_logging.EMPTY_VALUE

    def get_content_type(self, response):
        return response.content_type
