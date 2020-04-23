# coding=utf-8
import json
import logging
import sys
import uuid
from datetime import datetime
import traceback

from json_logging import util
from json_logging.framework_base import RequestAdapter, ResponseAdapter, AppRequestInstrumentationConfigurator, \
    FrameworkConfigurator
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


def get_correlation_id(request=None):
    """
    Get current request correlation-id. If one is not present, a new one might be generated
    depends on CREATE_CORRELATION_ID_IF_NOT_EXISTS setting value.

    :return: correlation-id string
    """
    return _request_util.get_correlation_id(request=request)


def register_framework_support(name, app_configurator, app_request_instrumentation_configurator, request_adapter_class,
                               response_adapter_class):
    """
    register support for a framework

    :param name: name of framework
    :param app_configurator: app pre-configurator class
    :param app_request_instrumentation_configurator: app configurator class
    :param request_adapter_class: request adapter class
    :param response_adapter_class: response adapter class
    """
    if not name:
        raise RuntimeError("framework name can not be null or empty")

    util.validate_subclass(request_adapter_class, RequestAdapter)
    util.validate_subclass(response_adapter_class, ResponseAdapter)
    util.validate_subclass(app_request_instrumentation_configurator, AppRequestInstrumentationConfigurator)
    if app_configurator is not None:
        util.validate_subclass(app_configurator, FrameworkConfigurator)

    name = name.lower()
    if name in _framework_support_map:
        ENABLE_JSON_LOGGING_DEBUG and _logger.warning("Re-register framework %s", name)
    _framework_support_map[name] = {
        'app_configurator': app_configurator,
        'app_request_instrumentation_configurator': app_request_instrumentation_configurator,
        'request_adapter_class': request_adapter_class,
        'response_adapter_class': response_adapter_class
    }


def config_root_logger():
    """
        You must call this if you are using root logger.
        Make all root logger' handlers produce JSON format
        & remove duplicate handlers for request instrumentation logging.
        Please made sure that you call this after you called "logging.basicConfig() or logging.getLogger('root')
    """
    if ENABLE_JSON_LOGGING:
        ENABLE_JSON_LOGGING_DEBUG and _logger.debug("Update root logger to using JSONLogFormatter")
        if len(logging.root.handlers) > 0:
            if _current_framework is None or _current_framework == '-':
                util.update_formatter_for_loggers([logging.root], JSONLogFormatter)
            else:
                util.update_formatter_for_loggers([logging.root], JSONLogWebFormatter)
                # remove all handlers for request logging
                request_logger = _current_framework['app_request_instrumentation_configurator']().get_request_logger()
                if request_logger:
                    for handler in request_logger.handlers:
                        request_logger.removeHandler(handler)
        else:
            _logger.error(
                "No logging handlers found for root logger. Please made sure that you call this after you called "
                "logging.basicConfig() or logging.getLogger('root')")


def init_non_web(*args, **kw):
    __init(*args, **kw)


def __init(framework_name=None, custom_formatter=None, enable_json=False):
    """
    Initialize JSON logging support, if no **framework_name** passed, logging will be initialized in non-web context.
    This is supposed to be called only one time.

    If **custom_formatter** is passed, it will (in non-web context) use this formatter over the default.

    :param framework_name: type of framework logging should support.
    :param custom_formatter: formatter to override default JSONLogFormatter.
    """

    global _current_framework
    global ENABLE_JSON_LOGGING
    if _current_framework is not None:
        raise RuntimeError("Can not call init more than once")

    if custom_formatter:
        if not issubclass(custom_formatter, logging.Formatter):
            raise ValueError('custom_formatter is not subclass of logging.Formatter', custom_formatter)

    ENABLE_JSON_LOGGING_DEBUG and _logger.info("init framework " + str(framework_name))

    if framework_name:
        framework_name = framework_name.lower()
        if framework_name not in _framework_support_map.keys():
            raise RuntimeError(framework_name + " is not a supported framework")

        _current_framework = _framework_support_map[framework_name]
        global _request_util
        _request_util = util.RequestUtil(request_adapter_class=_current_framework['request_adapter_class'],
                                         response_adapter_class=_current_framework['response_adapter_class'])

        if ENABLE_JSON_LOGGING and _current_framework['app_configurator'] is not None:
            _current_framework['app_configurator']().config()

        formatter = custom_formatter if custom_formatter else JSONLogWebFormatter
    else:
        formatter = custom_formatter if custom_formatter else JSONLogFormatter

    if not enable_json and not ENABLE_JSON_LOGGING:
        _logger.warning(
            "JSON format is not enable, normal log will be in plain text but request logging still in JSON format! "
            "To enable set ENABLE_JSON_LOGGING env var to either one of following values: ['true', '1', 'y', 'yes']")
    else:
        ENABLE_JSON_LOGGING = True
        logging._defaultFormatter = formatter()

    # go to all the initialized logger and update it to use JSON formatter
    ENABLE_JSON_LOGGING_DEBUG and _logger.debug("Update all existing logger to using JSONLogFormatter")
    existing_loggers = list(map(logging.getLogger, logging.Logger.manager.loggerDict))
    util.update_formatter_for_loggers(existing_loggers, formatter)


def init_request_instrument(app=None, custom_formatter=None):
    """
    Configure the request instrumentation logging configuration for given web app. Must be called after init method

    If **custom_formatter** is passed, it will use this formatter over the default.

    :param app: current web application instance
    :param custom_formatter: formatter to override default JSONRequestLogFormatter.
    """

    if _current_framework is None or _current_framework == '-':
        raise RuntimeError("please init the logging first, call init(framework_name) first")

    if custom_formatter:
        if not issubclass(custom_formatter, logging.Formatter):
            raise ValueError('custom_formatter is not subclass of logging.Formatter', custom_formatter)

    configurator = _current_framework['app_request_instrumentation_configurator']()
    configurator.config(app)

    formatter = custom_formatter if custom_formatter else JSONRequestLogFormatter
    request_logger = configurator.request_logger
    request_logger.setLevel(logging.DEBUG)
    request_logger.addHandler(logging.StreamHandler(sys.stdout))
    util.update_formatter_for_loggers([request_logger], formatter)


def get_request_logger():
    global _request_logger

    if _current_framework is None or _current_framework == '-':
        raise RuntimeError(
            "request_logger is only available if json_logging is inited with a web app, "
            "call init_<framework_name>() to do that")

    instance = _current_framework['app_request_instrumentation_configurator']._instance
    if instance is None:
        raise RuntimeError("please init request instrument first, call init_request_instrument(app) to do that")

    return instance.request_logger


class RequestInfo(dict):
    """
        class that keep HTTP request information for request instrumentation logging
    """

    def __init__(self, request, **kwargs):
        super(RequestInfo, self).__init__(**kwargs)
        utcnow = datetime.utcnow()
        self.request_start = utcnow
        self.request = request
        self.request_received_at = util.iso_time_format(utcnow)

    # noinspection PyAttributeOutsideInit
    def update_response_status(self, response):
        """
        update response information into this object, must be called before invoke request logging statement
        :param response:
        """
        response_adapter = _request_util.response_adapter
        utcnow = datetime.utcnow()
        time_delta = utcnow - self.request_start
        self.response_time_ms = int(time_delta.total_seconds()) * 1000 + int(time_delta.microseconds / 1000)
        self.response_status = response_adapter.get_status_code(response)
        self.response_size_b = response_adapter.get_response_size(response)
        self.response_content_type = response_adapter.get_content_type(response)
        self.response_sent_at = util.iso_time_format(utcnow)


class BaseJSONFormatter(logging.Formatter):
    """
       Base class for JSON formatters
    """
    base_object_common = {}

    def __init__(self, *args, **kw):
        super(BaseJSONFormatter, self).__init__(*args, **kw)
        if COMPONENT_ID and COMPONENT_ID != EMPTY_VALUE:
            self.base_object_common["component_id"] = COMPONENT_ID
        if COMPONENT_NAME and COMPONENT_NAME != EMPTY_VALUE:
            self.base_object_common["component_name"] = COMPONENT_NAME
        if COMPONENT_INSTANCE_INDEX and COMPONENT_INSTANCE_INDEX != EMPTY_VALUE:
            self.base_object_common["component_instance_idx"] = COMPONENT_INSTANCE_INDEX

    def format(self, record):
        log_object = self._format_log_object(record, request_util=_request_util)
        return JSON_SERIALIZER(log_object)

    def _format_log_object(self, record, request_util):
        utcnow = datetime.utcnow()
        base_obj = {
            "written_at": util.iso_time_format(utcnow),
            "written_ts": util.epoch_nano_second(utcnow),
        }
        base_obj.update(self.base_object_common)
        return base_obj


class JSONRequestLogFormatter(BaseJSONFormatter):
    """
       Formatter for HTTP request instrumentation logging
    """

    def _format_log_object(self, record, request_util):
        json_log_object = super(JSONRequestLogFormatter, self)._format_log_object(record, request_util)
        request = record.request_info.request
        request_adapter = request_util.request_adapter

        length = request_adapter.get_content_length(request)
        json_log_object.update({
            "type": "request",
            "correlation_id": request_util.get_correlation_id(request),
            "remote_user": request_adapter.get_remote_user(request),
            "request": request_adapter.get_path(request),
            "referer": request_adapter.get_http_header(request, 'referer', EMPTY_VALUE),
            "x_forwarded_for": request_adapter.get_http_header(request, 'x-forwarded-for', EMPTY_VALUE),
            "protocol": request_adapter.get_protocol(request),
            "method": request_adapter.get_method(request),
            "remote_ip": request_adapter.get_remote_ip(request),
            "request_size_b": util.parse_int(length, -1),
            "remote_host": request_adapter.get_remote_ip(request),
            "remote_port": request_adapter.get_remote_port(request),
            "request_received_at": record.request_info.request_received_at,
            "response_time_ms": record.request_info.response_time_ms,
            "response_status": record.request_info.response_status,
            "response_size_b": record.request_info.response_size_b,
            "response_content_type": record.request_info.response_content_type,
            "response_sent_at": record.request_info.response_sent_at
        })
        return json_log_object


def _sanitize_log_msg(record):
    return record.getMessage().replace('\n', '_').replace('\r', '_').replace('\t', '_')


class JSONLogFormatter(BaseJSONFormatter):
    """
    Formatter for non-web application log
    """

    def get_exc_fields(self, record):
        if record.exc_info:
            exc_info = self.format_exception(record.exc_info)
        else:
            exc_info = record.exc_text
        return {
            'exc_info': exc_info,
            'filename': record.filename,
        }

    @classmethod
    def format_exception(cls, exc_info):
        return ''.join(traceback.format_exception(*exc_info)) if exc_info else ''

    def _format_log_object(self, record, request_util):
        json_log_object = super(JSONLogFormatter, self)._format_log_object(record, request_util)
        json_log_object.update({
            "msg": _sanitize_log_msg(record),
            "type": "log",
            "logger": record.name,
            "thread": record.threadName,
            "level": record.levelname,
            "module": record.module,
            "line_no": record.lineno,
        })
        if hasattr(record, 'props'):
            json_log_object.update(record.props)

        if record.exc_info or record.exc_text:
            json_log_object.update(self.get_exc_fields(record))

        return json_log_object


class JSONLogWebFormatter(JSONLogFormatter):
    """
    Formatter for web application log
    """

    def _format_log_object(self, record, request_util):
        json_log_object = super(JSONLogWebFormatter, self)._format_log_object(record, request_util)
        json_log_object.update({
            "correlation_id": request_util.get_correlation_id(within_formatter=True),
        })
        return json_log_object


# register flask support
# noinspection PyPep8
import json_logging.framework.flask as flask_support

register_framework_support('flask', None, flask_support.FlaskAppRequestInstrumentationConfigurator,
                           flask_support.FlaskRequestAdapter,
                           flask_support.FlaskResponseAdapter)


def init_flask(custom_formatter=None, enable_json=False):
    __init(framework_name='flask', custom_formatter=custom_formatter, enable_json=enable_json)


# register sanic support
# noinspection PyPep8
from json_logging.framework.sanic import SanicAppConfigurator, SanicAppRequestInstrumentationConfigurator, \
    SanicRequestAdapter, SanicResponseAdapter

register_framework_support('sanic', SanicAppConfigurator,
                           SanicAppRequestInstrumentationConfigurator,
                           SanicRequestAdapter,
                           SanicResponseAdapter)


def init_sanic(custom_formatter=None, enable_json=False):
    __init(framework_name='sanic', custom_formatter=custom_formatter, enable_json=enable_json)


# register quart support
# noinspection PyPep8
import json_logging.framework.quart as quart_support

register_framework_support('quart', None, quart_support.QuartAppRequestInstrumentationConfigurator,
                           quart_support.QuartRequestAdapter,
                           quart_support.QuartResponseAdapter)


def init_quart(custom_formatter=None, enable_json=False):
    __init(framework_name='quart', custom_formatter=custom_formatter, enable_json=enable_json)


# register connexion support
# noinspection PyPep8
import json_logging.framework.connexion as connexion_support

register_framework_support('connexion', None, connexion_support.ConnexionAppRequestInstrumentationConfigurator,
                           connexion_support.ConnexionRequestAdapter,
                           connexion_support.ConnexionResponseAdapter)


def init_connexion(custom_formatter=None, enable_json=False):
    __init(framework_name='connexion', custom_formatter=custom_formatter, enable_json=enable_json)
