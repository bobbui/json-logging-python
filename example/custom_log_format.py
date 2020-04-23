# This example shows how the logger can be set up to use a custom JSON format.
import logging
import json
import traceback
from datetime import datetime
import copy
import json_logging
import sys

json_logging.ENABLE_JSON_LOGGING = True


def extra(**kw):
    '''Add the required nested props layer'''
    return {'extra': {'props': kw}}


class CustomJSONLog(logging.Formatter):
    """
    Customized logger
    """

    def get_exc_fields(self, record):
        if record.exc_info:
            exc_info = self.format_exception(record.exc_info)
        else:
            exc_info = record.exc_text
        return {'python.exc_info': exc_info}

    @classmethod
    def format_exception(cls, exc_info):
        return ''.join(traceback.format_exception(*exc_info)) if exc_info else ''

    def format(self, record):
        json_log_object = {"@timestamp": datetime.utcnow().isoformat(),
                           "level": record.levelname,
                           "message": record.getMessage(),
                           "caller": record.filename + '::' + record.funcName
                           }
        json_log_object['data'] = {
            "python.logger_name": record.name,
            "python.module": record.module,
            "python.funcName": record.funcName,
            "python.filename": record.filename,
            "python.lineno": record.lineno,
            "python.thread": record.threadName,
            "python.pid": record.process
        }
        if hasattr(record, 'props'):
            json_log_object['data'].update(record.props)

        if record.exc_info or record.exc_text:
            json_log_object['data'].update(self.get_exc_fields(record))

        return json.dumps(json_log_object)


# You would normally import logger_init and setup the logger in your main module - e.g.
# main.py

json_logging.init_non_web(custom_formatter=CustomJSONLog)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stderr))

logger.info('Starting')
try:
    1 / 0
except:  # noqa pylint: disable=bare-except
    logger.exception('You can\'t divide by zero')
