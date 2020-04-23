import logging
import sys

import json_logging

# log is initialized without a web framework name
json_logging.ENABLE_JSON_LOGGING = True
json_logging.init_non_web()

logger = logging.getLogger("test logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

logger.info("test log statement")
logger.info("test log statement with extra props", extra={'props': {"extra_property": 'extra_value'}})
