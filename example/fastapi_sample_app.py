import logging

import fastapi

import json_logging

app = fastapi.FastAPI()

# init the logger as usual
logger = logging.getLogger(__name__)

@app.get('/')
async def home():
    logger.info("test log statement")
    logger.info("test log statement with extra props", extra={'props': {"extra_property": 'extra_value'}})
    correlation_id = json_logging.get_correlation_id()
    return "hello world" \
           "\ncorrelation_id                    : " + correlation_id


@app.get('/exception')
def exception():
    try:
        raise RuntimeError
    except BaseException as e:
        logger.error("Error occurred", exc_info=e)
        logger.exception("Error occurred", exc_info=e)
    return "Error occurred, check log for detail"


@app.get('/exclude_from_request_instrumentation')
def exclude_from_request_instrumentation():
    return "this request wont log request instrumentation information"


if __name__ == "__main__":
    import uvicorn
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'default_handler': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
            },
        },
        'loggers': {
            '': {
                'handlers': ['default_handler'],
            }
        }
    }
    json_logging.init_fastapi(enable_json=True)
    json_logging.init_request_instrument(app, exclude_url_patterns=[r'^/exclude_from_request_instrumentation'])
    uvicorn.run(app, host='0.0.0.0', port=5000, log_level="debug", log_config=logging_config)
