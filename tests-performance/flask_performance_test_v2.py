import logging
import os
import sys
from logging import StreamHandler
from timeit import Timer

from flask import Flask
from flask import request as request

import json_logging

logger = logging.getLogger("test logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(StreamHandler(sys.stdout))
app = Flask(__name__)

json_logging.init(framework_name='flask')
json_logging.init_request_instrument(app)

FORMAT = 'important: %s'
MESSAGE = 'some important information to be logged'


@app.route('/')
def home________________():
    count_ = 10
    if 'count' in request.args:
        count_ = int(request.args['count'])
    simple_logging = Timer(lambda: logger.info(MESSAGE)).timeit(number=count_)
    formatted_logging = Timer(lambda: logger.info(FORMAT, MESSAGE)).timeit(number=count_)
    return "simple_logging : " + str(simple_logging) + " </br>" \
           + "formatted_logging " + str(formatted_logging) + " </br>" \
           + "aggregated " + str(formatted_logging)


port = os.getenv('PORT', '5002')
if __name__ == "__main__":
    app.debug = not os.getenv('PORT')
    logger.info("App started")
    app.run(host='0.0.0.0', port=int(port), use_reloader=False)
