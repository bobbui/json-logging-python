import logging, sys, json_logging, sanic

app = sanic.Sanic(name="sanic-web-app")
json_logging.init_sanic(enable_json=True)
json_logging.init_request_instrument(app)

# init the logger as usual
logger = logging.getLogger("sanic-integration-test-app")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

@app.route("/")
async def home(request):
    logger.info("test log statement")
    logger.info("test log statement with extra props", extra={'props': {"extra_property": 'extra_value'}})
    # this will be faster
    correlation_id = json_logging.get_correlation_id(request=request)
    # this will be slower, but will work in context you cant get a reference of request object
    correlation_id_without_request_obj = json_logging.get_correlation_id()

    return sanic.response.text("hello world")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
