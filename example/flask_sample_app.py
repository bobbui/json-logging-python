import logging
import sys

import flask

import json_logging

app = flask.Flask(__name__)
json_logging.init_flask(enable_json=True)
json_logging.init_request_instrument(
    app, exclude_url_patterns=[r'/ready', r'/alive'])

app.logger.setLevel(logging.getLevelName(env.get('LOGLEVEL', 'INFO').upper()))
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.removeHandler(default_handler)

app.config["MONGO_URI"] = env.get("MONGO_DSN")

client = MongoClient(app.config["MONGO_URI"])
app.logger.debug(client.server_info())
