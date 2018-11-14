import logging
import sys

import flask

import json_logging

app = flask.Flask(__name__)
json_logging.ENABLE_JSON_LOGGING = True
# json_logging.CREATE_CORRELATION_ID_IF_NOT_EXISTS = False
json_logging.init(framework_name='flask')
json_logging.init_request_instrument(app)

# init the logger as usual
logger = logging.getLogger("test logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

@app.route('/')
def home():
    logger.info("test log statement")
    logger.info("test log statement", extra={'props': {"extra_property": 'extra_value'}})
    return "Hello world"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(5000), use_reloader=False)
