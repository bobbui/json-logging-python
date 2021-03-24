import asyncio, logging, sys, json_logging, quart

app = quart.Quart(__name__)
json_logging.init_quart(enable_json=True)
json_logging.init_request_instrument(app)

# init the logger as usual
logger = logging.getLogger("test logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

@app.route('/')
async def home():
    logger.info("test log statement")
    logger.info("test log statement with extra props", extra={'props': {"extra_property": 'extra_value'}})
    correlation_id = json_logging.get_correlation_id()
    return "Hello world"

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app.run(host='0.0.0.0', port=int(5000), use_reloader=False, loop=loop)
