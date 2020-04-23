#!/usr/bin/env python3

import connexion
import json_logging


def post_greeting(name):
    return 'Hello {name}'.format(name=name)


def create():
    app = connexion.FlaskApp(__name__, port=9090, specification_dir='openapi/')
    json_logging.init_connexion(enable_json=True)
    json_logging.init_request_instrument(app)

    app.add_api('helloworld-api.yaml', arguments={'title': 'Hello World Example'})
    return app


if __name__ == '__main__':
    app = create()
    app.run()
