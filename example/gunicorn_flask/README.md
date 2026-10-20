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
- Logs written outside a request, such as worker startup and shutdown, get `-`. **This depends on PR #127** (issue
  #125) and is not in master until #127 merges. Without it, each such record gets a random ID.

## Gunicorn access log

`accesslog = None` in `gunicorn.conf.py` avoids a second access line per request. If you prefer Gunicorn's access
log, remove that line, and remember that you then get two records per request.

## Startup and preload

The example assumes Gunicorn's default startup, where each worker imports `app.py` after it forks. With
`--preload` (or `preload_app = True`) the module is imported once in the master process before forking, so
json-logging is initialised in the master and the workers inherit it. Do not assume the two configurations behave
identically; this example is tested only with the default.

`/ready` is a readiness probe. It is excluded from request logging, so probing it adds no records.

## Local test

`tests/test_gunicorn_flask.py` starts this example on a Unix socket, waits until `/ready` answers, sends two requests,
and checks the JSON output above. In CI (`CI=true`) a missing `gunicorn` fails the test; elsewhere it is skipped.

## Verification status

- The launch command and the record layout above were checked against a real Gunicorn 26.2.0 worker over a Unix socket
  (saved in `audit/logs/gunicorn-flask-successful-run-2026-10-19.log`).
- The automated test runs in CI on Linux. Recorded status: see the pull request.
