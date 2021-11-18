# coding=utf-8
import json
import logging
import sys
import uuid

from json_logging import util
from json_logging.dto import RequestResponseDTOBase, DefaultRequestResponseDTO
from json_logging.formatters import JSONRequestLogFormatter, JSONLogFormatter, JSONLogWebFormatter
from json_logging.framework_base import BaseRequestInfoExtractor, BaseResponseInfoExtractor, \
    BaseAppRequestInstrumentationConfigurator, \
    BaseFrameworkConfigurator
from json_logging.util import get_library_logger, is_env_var_toggle

CORRELATION_ID_GENERATOR = uuid.uuid1
ENABLE_JSON_LOGGING = False
if is_env_var_toggle("ENABLE_JSON_LOGGING"):
    ENABLE_JSON_LOGGING = True

ENABLE_JSON_LOGGING_DEBUG = False
EMPTY_VALUE = '-'
CREATE_CORRELATION_ID_IF_NOT_EXISTS = True
JSON_SERIALIZER = lambda log: json.dumps(log, ensure_ascii=False)
CORRELATION_ID_HEADERS = ['X-Correlation-ID', 'X-Request-ID']
COMPONENT_ID = EMPTY_VALUE
COMPONENT_NAME = EMPTY_VALUE
COMPONENT_INSTANCE_INDEX = 0

_framework_support_map = {}
_current_framework = None
_logger = get_library_logger(__name__)
_request_util = None
_default_formatter = None


def get_correlation_id(request=None):
    """
    Get current request correlation-id. If one is not present, a new one might be generated
    depends on CREATE_CORRELATION_ID_IF_NOT_EXISTS setting value.

    :return: correlation-id string
    """
    return _request_util.get_correlation_id(request=request)


def config_root_logger():
    """
        You must call this if you are using root logger.
        Make all root logger' handlers produce JSON format
        & remove duplicate handlers for request instrumentation logging.
        Please made sure that you call this after you called "logging.basicConfig() or logging.getLogger()
    """

    if not logging.root.handlers:
        _logger.error(
            "No logging handlers found for root logger. Please made sure that you call this after you called "
            "logging.basicConfig() or logging.getLogger()")
        return

    if ENABLE_JSON_LOGGING:
        ENABLE_JSON_LOGGING_DEBUG and _logger.debug("Update root logger to using JSONLogFormatter")

        global _default_formatter
        util.update_formatter_for_loggers([logging.root], _default_formatter)


def init_non_web(*args, **kw):
    """
    Initialize for a non HTTP application
    :param args:
    :param kw:
    """
    __init(*args, **kw)


def __init(framework_name=None, custom_formatter=None, enable_json=False):
    """
    Initialize JSON logging support, if no **framework_name** passed, logging will be initialized in non-web context.
    This is supposed to be called only one time.

    If **custom_formatter** is passed, it will (in non-web context) use this formatter over the default.

    :param framework_name: type of framework logging should support.DEFAULT_CORRELATION_ID_HEADERS
    :param custom_formatter: formatter to override default JSONLogFormatter.
    """

    global _current_framework
    global ENABLE_JSON_LOGGING
    global _default_formatter

    if _current_framework is not None:
        raise RuntimeError("Can not call init more than once")

    if custom_formatter:
        if not issubclass(custom_formatter, logging.Formatter):
            raise ValueError('custom_formatter is not subclass of logging.Formatter', custom_formatter)

    if not enable_json and not ENABLE_JSON_LOGGING:
        _logger.warning(
            "JSON format is not enabled, normal log will be in plain text but request logging still in JSON format! "
            "To enable set ENABLE_JSON_LOGGING env var to either one of following values: ['true', '1', 'y', 'yes']")
    else:
        ENABLE_JSON_LOGGING = True

    ENABLE_JSON_LOGGING_DEBUG and _logger.info("init framework " + str(framework_name))

    if framework_name:
        framework_name = framework_name.lower()
        if framework_name not in _framework_support_map.keys():
            raise RuntimeError(framework_name + " is not a supported framework")

        global _request_util

        _current_framework = _framework_support_map[framework_name]
        _request_util = util.RequestUtil(
            request_info_extractor_class=_current_framework['request_info_extractor_class'],
            response_info_extractor_class=_current_framework['response_info_extractor_class'])

        if ENABLE_JSON_LOGGING and _current_framework['app_configurator'] is not None:
            _current_framework['app_configurator']().config()

        _default_formatter = custom_formatter if custom_formatter else JSONLogWebFormatter
    else:
        _default_formatter = custom_formatter if custom_formatter else JSONLogFormatter

    if ENABLE_JSON_LOGGING:
        logging._defaultFormatter = _default_formatter()

        _logger.debug("Update all existing logger to using JSONLogFormatter")

        existing_loggers = list(map(logging.getLogger, logging.Logger.manager.loggerDict))
        util.update_formatter_for_loggers(existing_loggers, _default_formatter)


def init_request_instrument(app=None, custom_formatter=None, exclude_url_patterns=[],
                            request_response_dto_class=DefaultRequestResponseDTO):
    """
    Configure the request instrumentation logging configuration for given web app. Must be called after init method

    If **custom_formatter** is passed, it will use this formatter over the default.

    :param app: current web application instance
    :param custom_formatter: formatter to override default JSONRequestLogFormatter.
    :param request_response_dto_class: request_response_dto_class to override default json_logging.RequestResponseDataExtractor.
    """

    if _current_framework is None or _current_framework == '-':
        raise RuntimeError("please init the logging first, call init(framework_name) first")

    if custom_formatter:
        if not issubclass(custom_formatter, logging.Formatter):
            raise ValueError('custom_formatter is not subclass of logging.Formatter', custom_formatter)

    if not issubclass(request_response_dto_class, RequestResponseDTOBase):
        raise ValueError('request_response_dto_class is not subclass of json_logging.RequestInfoBase',
                         custom_formatter)

    configurator = _current_framework['app_request_instrumentation_configurator']()
    configurator.config(app, request_response_dto_class, exclude_url_patterns=exclude_url_patterns)

    formatter = custom_formatter if custom_formatter else JSONRequestLogFormatter
    request_logger = configurator.request_logger
    request_logger.setLevel(logging.DEBUG)
    request_logger.addHandler(logging.StreamHandler(sys.stdout))
    util.update_formatter_for_loggers([request_logger], formatter)
    request_logger.parent = None


def get_request_logger():
    if _current_framework is None or _current_framework == '-':
        raise RuntimeError(
            "request_logger is only available if json_logging is inited with a web app, "
            "call init_<framework_name>() to do that")

    instance = _current_framework['app_request_instrumentation_configurator']._instance
    if instance is None:
        raise RuntimeError("please init request instrument first, call init_request_instrument(app) to do that")

    return instance.request_logger


import json_logging.frameworks


def init_flask(custom_formatter=None, enable_json=False):
    __init(framework_name='flask', custom_formatter=custom_formatter, enable_json=enable_json)


def init_sanic(custom_formatter=None, enable_json=False):
    __init(framework_name='sanic', custom_formatter=custom_formatter, enable_json=enable_json)


def init_quart(custom_formatter=None, enable_json=False):
    __init(framework_name='quart', custom_formatter=custom_formatter, enable_json=enable_json)


def init_connexion(custom_formatter=None, enable_json=False):
    __init(framework_name='connexion', custom_formatter=custom_formatter, enable_json=enable_json)


def init_fastapi(custom_formatter=None, enable_json=False):
    __init(framework_name='fastapi', custom_formatter=custom_formatter, enable_json=enable_json)
