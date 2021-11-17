# coding=utf-8
import logging
import sys

import json_logging
import json_logging.framework
from json_logging import JSONLogWebFormatter
from json_logging.framework_base import BaseAppRequestInstrumentationConfigurator, BaseRequestInfoExtractor, \
    BaseResponseInfoExtractor
from json_logging.util import is_not_match_any_pattern


def is_quart_present():
    # noinspection PyPep8,PyBroadException
    try:
        from quart import Quart
        return True
    except:
        return False


if is_quart_present():
    from quart import request as request_obj
    import quart as quart

    _current_request = request_obj
    _quart = quart


class QuartAppRequestInstrumentationConfigurator(BaseAppRequestInstrumentationConfigurator):
    def config(self, app, request_response_dto_class, exclude_url_patterns=[]):
        if not is_quart_present():
            raise RuntimeError("quart is not available in system runtime")
        from quart.app import Quart
        if not isinstance(app, Quart):
            raise RuntimeError("app is not a valid quart.app.Quart app instance")

        # Remove quart logging handlers
        from quart.logging import default_handler
        logging.getLogger('quart.app').removeHandler(default_handler)
        json_logging.util.update_formatter_for_loggers([
            logging.getLogger('quart.app'),
        ], JSONLogWebFormatter)

        logging.getLogger('quart.serving').disabled = True

        # noinspection PyAttributeOutsideInit
        self.request_logger = logging.getLogger('quart-request-logger')

        from quart import g

        @app.before_request
        def before_request():
            if is_not_match_any_pattern(_current_request.path, exclude_url_patterns):
                g.request_response_data = request_response_dto_class(_current_request)

        @app.after_request
        def after_request(response):
            if hasattr(g, 'request_response_data'):
                request_response_data = g.request_response_data
                request_response_data.on_request_complete(response)
                # TODO:handle to print out request instrumentation in non-JSON mode
                self.request_logger.info("", extra={'request_response_data': request_response_data})
            return response


class QuartRequestInfoExtractor(BaseRequestInfoExtractor):
    @staticmethod
    def get_request_class_type():
        raise NotImplementedError

    @staticmethod
    def support_global_request_object():
        return True

    @staticmethod
    def get_current_request():
        return _current_request

    def get_remote_user(self, request):
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
        try:
            _quart.g.correlation_id = value
        except:
            pass

    def get_correlation_id_in_request_context(self, request):
        try:
            return _quart.g.get('correlation_id', None)
        except:
            return None

    def get_protocol(self, request):
        return request.scheme

    def get_path(self, request):
        return request.path

    def get_content_length(self, request):
        return request.content_length

    def get_method(self, request):
        return request.method

    def get_remote_ip(self, request):
        return request.remote_addr

    def get_remote_port(self, request):
        return (
            request.host.split(":", 2)[1]
            if len(request.host.split(":", 2)) == 2
            else None
        )


class QuartResponseInfoExtractor(BaseResponseInfoExtractor):
    def get_status_code(self, response):
        return response.status_code

    def get_response_size(self, response):
        return response.content_length

    def get_content_type(self, response):
        return response.content_type
