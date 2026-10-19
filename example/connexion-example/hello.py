#!/usr/bin/env python3
import logging
import sys

import connexion
import json_logging

# init the logger as usual
logger = logging.getLogger("test logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))


def post_greeting(name):
    logger.info("test log statement")
    logger.info("test log statement with extra props", extra={'props': {"extra_property": 'extra_value'}})
    return f'Hello {name}'


def exclude_from_request_instrumentation(name):
    return f'Hello {name}. this request wont log request instrumentation information'


def create():
    app = connexion.FlaskApp(__name__, port=9090, specification_dir='openapi/')
    json_logging.init_connexion(enable_json=True)
    json_logging.init_request_instrument(app, exclude_url_patterns=[r'/exclude_from_request_instrumentation'])

    app.add_api('helloworld-api.yaml', arguments={'title': 'Hello World Example'})
    return app


if __name__ == '__main__':
    app = create()
    app.run()
