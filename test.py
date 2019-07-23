# Create the application instance
import logging
import sys
from logging.handlers import TimedRotatingFileHandler

import connexion

import json_logging

app = connexion.App(__name__, specification_dir='./')

json_logging.ENABLE_JSON_LOGGING = True
json_logging.init_connexion()
json_logging.init_request_instrument(app)

json_logging._logger
logger = logging.getLogger("test-logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

handler = TimedRotatingFileHandler('info.log', 'midnight', 1, utc=True)
logger.addHandler(handler)

if __name__ == '__main__':
    app.run()