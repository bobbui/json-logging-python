# This example shows how the logger can be set up to use a custom JSON format.
import json
import logging
import sys

import json_logging
import json_logging.formatters


def extra(**kw):
    '''Add the required nested props layer'''
    return {'extra': {'props': kw}}


class CustomJSONLog(json_logging.formatters.JSONLogFormatter):
    """
    Customized logger
    """

    def format(self, record):
        json_customized_log_object = ({
            "customized_prop": "customized value",
            "message": record.getMessage()
        })

        return json.dumps(json_customized_log_object)


# You would normally import logger_init and setup the logger in your main module - e.g.
# main.py

json_logging.init_non_web(custom_formatter=CustomJSONLog, enable_json=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stderr))

logger.info('sample log message')
