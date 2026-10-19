import json
import logging
import sys

import flask

import json_logging
import json_logging.dto
import json_logging.formatters


class CustomRequestJSONLog(json_logging.formatters.JSONRequestLogFormatter):
    """
    Customized logger
    """

    def _format_log_object(self, record, request_util):
        # request and response object can be extracted from record like this
        request = record.request_response_data._request
        response = record.request_response_data._response

        json_log_object = super()._format_log_object(record, request_util)
        json_log_object.update({
            "customized_prop": "customized value",
        })
        return json_log_object


class CustomDefaultRequestResponseDTO(json_logging.dto.DefaultRequestResponseDTO):
    """
        custom implementation
    """

    def __init__(self, request, **kwargs):
        super().__init__(request, **kwargs)

    def on_request_complete(self, response):
        super().on_request_complete(response)
        self.status = response.status


app = flask.Flask(__name__)
json_logging.init_flask(enable_json=True)
json_logging.init_request_instrument(app, exclude_url_patterns=[r'/exclude_from_request_instrumentation'],
                                     custom_formatter=CustomRequestJSONLog,
                                     request_response_dto_class=CustomDefaultRequestResponseDTO)

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
