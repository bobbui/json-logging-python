import json_logging
import logging
import sanic
import sys

app = sanic.Sanic()
json_logging.ENABLE_JSON_LOGGING = True
json_logging.init(framework_name='sanic')
json_logging.init_request_instrument(app)

# init the logger as usual
logger = logging.getLogger("sanic-integration-test-app")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))


@app.route("/")
async def test(request):
    logger.info("test log statement")
    logger.info("test log statement", extra={'props': {"extra_property": 'extra_value'}})
    return sanic.response.text("hello world")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
