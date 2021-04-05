import json
import logging
import sys

import flask

import json_logging


class CustomRequestJSONLog(json_logging.JSONLogWebFormatter):
    """
    Customized logger
    """

    def format(self, record):
        json_customized_log_object = ({
            "customized_prop": "customized value",
            "correlation_id": json_logging.get_correlation_id(),
        })
        return json.dumps(json_customized_log_object)


app = flask.Flask(__name__)
json_logging.init_flask(enable_json=True)
json_logging.init_request_instrument(app, exclude_url_patterns=[r'/exclude_from_request_instrumentation'],
                                     custom_formatter=CustomRequestJSONLog)

# init the logger as usual
logger = logging.getLogger("test logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))


@app.route('/')
def home():
    logger.info("test log statement")
    logger.info("test log statement with extra props", extra={'props': {"extra_property": 'extra_value'}})
    correlation_id = json_logging.get_correlation_id()
    return "hello world" \
           "\ncorrelation_id                    : " + correlation_id


@app.route('/exception')
def exception():
    try:
        raise RuntimeError
    except BaseException as e:
        logger.error("Error occurred", exc_info=e)
        logger.exception("Error occurred", exc_info=e)
    return "Error occurred, check log for detail"


@app.route('/exclude_from_request_instrumentation')
def exclude_from_request_instrumentation():
    return "this request wont log request instrumentation information"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(5000), use_reloader=False)
