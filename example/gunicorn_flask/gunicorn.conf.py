"""Gunicorn settings for the json-logging example.

Request instrumentation already writes one JSON request record per request, so Gunicorn's own access log is turned
off to avoid duplicate access lines (accesslog = "-" would write it to stdout). errorlog = "-" writes Gunicorn's
error log to stderr; its records are JSON only in the workers, after json-logging is initialised.
"""
import os

bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
workers = 2
accesslog = None
errorlog = "-"
loglevel = "info"
