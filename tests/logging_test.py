import datetime, logging, sys, json_logging, flask

app = flask.Flask(__name__)

logger_other = logging.getLogger("other")

def print_logger() -> None:
    for k, v in logging.Logger.manager.loggerDict.items():
        print('+ [%s] {%s} ' % (str.ljust(k, 20), str(v.__class__)[8:-2]))
        if isinstance(v, logging.PlaceHolder):
            continue
        for h in v.handlers:
            print('     +++', str(h.__class__)[8:-2])

@app.route('/')
def home():
    logger_other.info("foo")
    logger.info("test log statement")
    logger.info("test log statement with extra props", extra={'props': {"extra_property": 'extra_value'}})
    correlation_id = json_logging.get_correlation_id()
    return "Hello world : " + str(datetime.datetime.now())


if __name__ == "__main__":
    json_logging.init_flask(enable_json=True)
    json_logging.init_request_instrument(app)

    # init the logger as usual
    logger = logging.getLogger("test-logger")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(sys.stdout))

    print_logger()
    app.run(host='0.0.0.0', port=int(5000), use_reloader=False)