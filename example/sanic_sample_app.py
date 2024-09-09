#!/usr/bin/env python3

import logging
import sys

# noinspection PyPackageRequirements
import sanic

import json_logging

app = sanic.Sanic(name="sanic-web-app")
json_logging.init_sanic(enable_json=True)
json_logging.init_request_instrument(app, exclude_url_patterns=[r"/exclude_from_request_instrumentation"])

# init the logger as usual
logger = logging.getLogger("sanic-integration-test-app")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))


@app.route("/")
def test(request):
    logger.info("test log statement")
    logger.info("test log statement with extra props", extra={"props": {"extra_property": "extra_value"}})
    # this will be faster
    correlation_id = json_logging.get_correlation_id(request=request)
    # this will be slower, but will work in context you cant get a reference of request object
    correlation_id_without_request_obj = json_logging.get_correlation_id()

    return sanic.response.text(
        "hello world"
        f"\ncorrelation_id                    : {correlation_id}"
        f"\ncorrelation_id_without_request_obj: {correlation_id_without_request_obj}"
    )


@app.route("/exclude_from_request_instrumentation")
def exclude_from_request_instrumentation(request):
    return sanic.response.text("this request wont log request instrumentation information")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
