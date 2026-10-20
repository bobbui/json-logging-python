"""Flask application for Gunicorn. json-logging is initialised at import time, once per worker process."""
import logging

import flask
import json_logging

app = flask.Flask(__name__)
json_logging.init_flask(enable_json=True)
# /ready is a readiness probe: it is excluded from request logging so that probing never adds records.
json_logging.init_request_instrument(app, exclude_url_patterns=[r"^/ready$"])

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


@app.route("/")
def home():
    logger.info("handled request")
    return {"correlation_id": json_logging.get_correlation_id()}


@app.route("/ready")
def ready():
    return "ok"
