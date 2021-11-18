import logging
import sys
import traceback
from datetime import datetime

import json_logging

# The list contains all the attributes listed in that will not be overwritten by custom extra props
# http://docs.python.org/library/logging.html#logrecord-attributes
LOG_RECORD_BUILT_IN_ATTRS = [
    'asctime', 'created', 'exc_info', 'exc_text', 'filename', 'args',
    'funcName', 'id', 'levelname', 'levelno', 'lineno', 'module', 'msg',
    'msecs', 'msecs', 'message', 'name', 'pathname', 'process',
    'processName', 'relativeCreated', 'thread', 'threadName', 'extra',
    # Also exclude legacy 'props'
    'props',
]

# python 2 compatible check
try:
    basestring
except NameError:
    basestring = str

if sys.version_info < (3, 0):
    EASY_SERIALIZABLE_TYPES = (basestring, bool, dict, float, int, list, type(None))
else:
    LOG_RECORD_BUILT_IN_ATTRS.append('stack_info')
    EASY_SERIALIZABLE_TYPES = (str, bool, dict, float, int, list, type(None))


def _sanitize_log_msg(record):
    """
    Sanitize log message to make sure we can print out properly formatted JSON string
    :param record: log object
    :return: sanitized log object
    """
    return record.getMessage().replace('\n', '_').replace('\r', '_').replace('\t', '_')


class BaseJSONFormatter(logging.Formatter):
    """
       Base class for JSON formatters
    """
    base_object_common = {}

    def __init__(self, *args, **kw):
        super(BaseJSONFormatter, self).__init__(*args, **kw)
        if json_logging.COMPONENT_ID and json_logging.COMPONENT_ID != json_logging.EMPTY_VALUE:
            self.base_object_common["component_id"] = json_logging.COMPONENT_ID
        if json_logging.COMPONENT_NAME and json_logging.COMPONENT_NAME != json_logging.EMPTY_VALUE:
            self.base_object_common["component_name"] = json_logging.COMPONENT_NAME
        if json_logging.COMPONENT_INSTANCE_INDEX and json_logging.COMPONENT_INSTANCE_INDEX != json_logging.EMPTY_VALUE:
            self.base_object_common["component_instance_idx"] = json_logging.COMPONENT_INSTANCE_INDEX

    def format(self, record):
        """
            Format the specified record as text. Overriding default python logging implementation
        """
        log_object = self._format_log_object(record, request_util=json_logging._request_util)
        return json_logging.JSON_SERIALIZER(log_object)

    def _format_log_object(self, record, request_util):
        utcnow = datetime.utcnow()

        base_obj = {
            "written_at": json_logging.util.iso_time_format(utcnow),
            "written_ts": json_logging.util.epoch_nano_second(utcnow),
        }

        base_obj.update(self.base_object_common)
        # Add extra fields
        base_obj.update(self._get_extra_fields(record))

        return base_obj

    def _get_extra_fields(self, record):
        """
        Get the dict of custom extra fields passed to the log statement
        :param record: log record
        :return:
        """
        fields = {}

        if record.args:
            fields['msg'] = record.msg

        for key, value in record.__dict__.items():
            if key not in LOG_RECORD_BUILT_IN_ATTRS:
                if isinstance(value, EASY_SERIALIZABLE_TYPES):
                    fields[key] = value
                else:
                    # try to cast it to a string representation
                    fields[key] = repr(value)

        # Always add 'props' to the root of the log, assumes props is a dict
        if hasattr(record, 'props') and isinstance(record.props, dict):
            fields.update(record.props)

        return fields


class JSONLogFormatter(BaseJSONFormatter):
    """
    Default formatter for non-web application log
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

        if record.exc_info or record.exc_text:
            json_log_object.update(self.get_exc_fields(record))

        return json_log_object


class JSONLogWebFormatter(JSONLogFormatter):
    """
    Formatter for web application log with correlation-id
    """

    def _format_log_object(self, record, request_util):
        json_log_object = super(JSONLogWebFormatter, self)._format_log_object(record, request_util)

        if "correlation_id" not in json_log_object:
            json_log_object.update({
                "correlation_id": request_util.get_correlation_id(within_formatter=True),
            })

        return json_log_object


class JSONRequestLogFormatter(BaseJSONFormatter):
    """
       Formatter for HTTP request instrumentation logging
    """

    def _format_log_object(self, record, request_util):
        json_log_object = super(JSONRequestLogFormatter, self)._format_log_object(record, request_util)

        request_adapter = request_util.request_adapter
        response_adapter = request_util.response_adapter

        request = record.request_response_data._request
        response = record.request_response_data._response

        length = request_adapter.get_content_length(request)

        json_log_object.update({
            "type": "request",
            "correlation_id": request_util.get_correlation_id(request),
            "remote_user": request_adapter.get_remote_user(request),
            "request": request_adapter.get_path(request),
            "referer": request_adapter.get_http_header(request, 'referer', json_logging.EMPTY_VALUE),
            "x_forwarded_for": request_adapter.get_http_header(request, 'x-forwarded-for', json_logging.EMPTY_VALUE),
            "protocol": request_adapter.get_protocol(request),
            "method": request_adapter.get_method(request),
            "remote_ip": request_adapter.get_remote_ip(request),
            "request_size_b": json_logging.util.parse_int(length, -1),
            "remote_host": request_adapter.get_remote_ip(request),
            "remote_port": request_adapter.get_remote_port(request),
            "response_status": response_adapter.get_status_code(response),
            "response_size_b": response_adapter.get_response_size(response),
            "response_content_type": response_adapter.get_content_type(response),
        })

        json_log_object.update(record.request_response_data)

        return json_log_object
