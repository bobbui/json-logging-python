# Flask under Gunicorn with json-logging

`app.py` initialises json-logging once per Gunicorn worker process, at import time, and enables request
instrumentation. `gunicorn.conf.py` turns off Gunicorn's own access log, because json-logging already writes one JSON
request record per request.

## Run

```bash
cd example/gunicorn_flask
gunicorn -c gunicorn.conf.py app:app
curl -H "X-Correlation-ID: demo-1" http://127.0.0.1:8000/
```

## What you should see

| Output | Format | Notes |
|---|---|---|
| Gunicorn startup and master messages (`Starting gunicorn`, `Listening at`, `Booting worker`) | plain text | json-logging does not run in the master process, so these stay plain text |
| `json_logging` "Update all existing logger" lines at worker start | JSON | emitted when each worker initialises; harmless |
| application logs (`logger: "app"`) | JSON | `correlation_id` is the request's `X-Correlation-ID`, or a generated ID |
| request records (`type: "request"`) | JSON | same `correlation_id` as the application logs of that request |
| `gunicorn.error` records, such as `Worker exiting` | JSON in workers | `correlation_id` is `-`: they are outside any request |

## Correlation across requests

- A request that sends `X-Correlation-ID` (or `X-Request-ID`) keeps that value in every application and request log
  it produces.
- A request without a header gets one generated ID, shared by its application and request logs. Different requests
  get different IDs.
- Logs written outside a request, such as worker startup and shutdown, get `-`. This needs the fix for #125; before
  that fix, each such record got a random ID.

## Gunicorn access log

`accesslog = None` in `gunicorn.conf.py` avoids a second access line per request. If you prefer Gunicorn's access
log, remove that line, and remember that you then get two records per request.

## Local test

`tests/test_gunicorn_flask.py` starts this example on a Unix socket, sends two requests, and checks the JSON output
above. It is skipped if `gunicorn` is not installed.

## Verification status

- The launch command and the record layout above were checked against a real Gunicorn 26.2.0 worker over a Unix socket
  (saved in `audit/logs/gunicorn-flask-successful-run-2026-10-19.log`).
- The automated test runs in CI on Linux. Recorded status: see the pull request.
