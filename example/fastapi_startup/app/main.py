"""Module-level FastAPI setup. Create the app and call json_logging.init_* exactly once per process.

Start it with either of the working patterns in example/fastapi_startup/README.md. Do not run this file as a
script (`python app/main.py`) while also passing an import string such as "app.main:app" to uvicorn.
"""
import logging

import fastapi
import json_logging

app = fastapi.FastAPI()
json_logging.init_fastapi(enable_json=True)
json_logging.init_request_instrument(app)

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


@app.get("/")
def home():
    logger.info("handled request")
    return {"correlation_id": json_logging.get_correlation_id()}
