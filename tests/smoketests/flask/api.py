import os
import datetime, logging, sys, json_logging, flask

app = flask.Flask(__name__)
json_logging.init_flask(enable_json=True)
json_logging.init_request_instrument(app)

# init the logger as usual
logger = logging.getLogger("test-logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

@app.route('/')
def home():
    logger.info("test log statement")
    logger.info("test log statement with extra props", extra={'props': {"extra_property": 'extra_value'}})
    correlation_id = json_logging.get_correlation_id()
    return "Hello world : " + str(datetime.datetime.now())

if __name__ == "__main__":
    port = os.getenv('PORT', '5000')
    app.run(host='0.0.0.0', port=int(port), use_reloader=False)
