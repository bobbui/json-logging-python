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
| `gunicorn.error` records written by a worker, such as `Worker exiting` | JSON | json-logging reformats the loggers that exist when the worker initialises it. Outside a request `correlation_id` should be `-`, but that needs PR #127 (see below); without it each record gets a random ID |

## Correlation across requests

- A request that sends `X-Correlation-ID` (or `X-Request-ID`) keeps that value in every application and request log
  it produces.
- A request without a header gets one generated ID, shared by its application and request logs. Different requests
  get different IDs.
- Logs written outside a request, such as worker startup and shutdown, get `-`. **This depends on PR #127** (issue
  #125) and is not in master until #127 merges. Without it, each such record gets a random ID.

## Gunicorn access log

Gunicorn's access log is off unless you configure it; `accesslog = None` in `gunicorn.conf.py` states that default
explicitly. Removing the line does not turn the access log on. To enable it, set a destination:

```python
accesslog = "-"                            # stdout
# accesslog = "/var/log/app/access.log"    # or a file path
```

or pass `--access-logfile -` on the command line. json-logging's request instrumentation still writes its own JSON
request record, so each HTTP request then produces two access records: Gunicorn's line and json-logging's record.
In the workers, Gunicorn's access line is itself wrapped in a JSON record with `"logger": "gunicorn.access"`. Keep the
access log off unless you need Gunicorn's format as well.

## Startup and preload

The example assumes Gunicorn's default startup, where each worker imports `app.py` after it forks. With
`--preload` (or `preload_app = True`) the module is imported once in the master process before forking, so
json-logging is initialised in the master and the workers inherit it. Do not assume the two configurations behave
identically; this example is tested only with the default.

`/ready` is a readiness probe. It is excluded from request logging, so probing it adds no records.

## Local test

`tests/test_gunicorn_flask.py` starts this example on a Unix socket, waits until `/ready` answers, sends two requests,
and checks the output above: application and request records share each request's correlation ID, `/ready` is not
logged, there is no Gunicorn access line, and the worker's `Worker exiting` record is JSON. A second test enables
`--access-logfile -` and checks that the access-line detector does find the extra lines. In CI (`CI=true`) a missing
`gunicorn` fails the tests; elsewhere they are skipped.

## Verification status

- The launch command and the record layout above were checked by hand against a real Gunicorn 26.2.0 worker over a
  Unix socket, with and without `--access-logfile -`.
- The automated tests run in CI on Linux. Recorded status: see the pull request.
