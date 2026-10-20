"""Flask application for Gunicorn. json-logging is initialised at import time, once per worker process."""
import logging

import flask
import json_logging

app = flask.Flask(__name__)
json_logging.init_flask(enable_json=True)
json_logging.init_request_instrument(app)

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


@app.route("/")
def home():
    logger.info("handled request")
    return {"correlation_id": json_logging.get_correlation_id()}
