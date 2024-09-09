import datetime
import logging
import os
import sys

import fastapi
import uvicorn

import json_logging

app = fastapi.FastAPI()
json_logging.init_fastapi(enable_json=True)
json_logging.init_request_instrument(app)

# init the logger as usual
logger = logging.getLogger("test-logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))


@app.get("/")
def home():
    logger.info("test log statement")
    logger.info("test log statement with extra props", extra={"props": {"extra_property": "extra_value"}})
    correlation_id = json_logging.get_correlation_id()
    return "Hello world : " + str(datetime.datetime.now())


if __name__ == "__main__":
    port = os.getenv("PORT", "5000")
    uvicorn.run(app, host="0.0.0.0", port=int(port))
