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

The output mixes plain text and JSON. Gunicorn's master process never runs json-logging; each worker initialises it
when it imports `app.py`.

| Output | Stream | Format | Notes |
|---|---|---|---|
| Gunicorn master and boot messages (`Starting gunicorn`, `Listening at`, `Booting worker`) | stderr | plain text | written by the master, or by a worker before it has initialised json-logging |
| `json_logging` "Update all existing logger" line, once per worker | stdout | JSON | appears when JSON is enabled and the root logger has no handlers; harmless |
| `worker ready` application log, once per worker | stderr | JSON | logged outside any request, so `correlation_id` is `-` |
| application logs during a request (`logger: "app"`) | stderr | JSON | `correlation_id` is the request's ID (see below) |
| request records (`type: "request"`) | stdout | JSON | json-logging's request instrumentation; same `correlation_id` as that request's application logs |
| `gunicorn.error` records written by a worker, such as `Worker exiting` | stderr | JSON | outside any request, so `correlation_id` is `-` |

## Correlation IDs

- A request that sends `X-Correlation-ID` keeps that value in every application and request log it produces. If that
  header is absent, `X-Request-ID` is used (`json_logging.CORRELATION_ID_HEADERS` sets the order).
- A request without either header gets one generated ID, shared by its application and request logs. Different
  requests get different IDs.
- Logs written outside a request, such as worker startup and shutdown, get `-` (`json_logging.EMPTY_VALUE`).

## Gunicorn access and error logs

| Setting | Effect |
|---|---|
| `accesslog = None` (this example, and Gunicorn's default) | no Gunicorn access log |
| `accesslog = "-"` or `--access-logfile -` | Gunicorn access log on **stdout** |
| `accesslog = "/path/access.log"` | Gunicorn access log in that file |
| `errorlog = "-"` (this example) | Gunicorn error log on **stderr** |

Removing `accesslog = None` does not turn the access log on; you must set a destination. Gunicorn's access log is
separate from json-logging's request instrumentation, so with both enabled each HTTP request produces two access
records: Gunicorn's line (in a worker, wrapped in a JSON record with `"logger": "gunicorn.access"`) and json-logging's
request record. Keep Gunicorn's access log off unless you need its format as well.

## Scope: worker class, preload and custom logging configuration

This example and its tests use Gunicorn's default **sync** worker, Gunicorn's built-in logging setup, and the default
startup in which each worker imports `app.py` after it forks.

- **gevent and other worker classes** (issue #25 uses `worker_class = "gevent"`) are not exercised by these tests.
- **`--preload`** (`preload_app = True`) imports `app.py` once in the master before forking, so json-logging is
  initialised in the master and the workers inherit it. This is not tested here either.
- **A custom `logconfig` / `logging.conf`** changes which handlers exist and where they write. When `init_flask()`
  runs in a worker, it replaces the formatter of every handler on every named logger that exists at that moment,
  including `gunicorn.error`, `gunicorn.access` and loggers from your `logging.conf`, so custom formats on those
  handlers become JSON. Handlers on the **root** logger are not changed unless you also call
  `json_logging.config_root_logger()` after the logging configuration has been applied.

To adapt the example to an existing setup such as the one in issue #25, keep its two essentials: call
`json_logging.init_flask(enable_json=True)` and `json_logging.init_request_instrument(app)` in the module the workers
import, and either turn Gunicorn's access log off or accept the duplicate records. Then check the output of your own
configuration (worker class, `logconfig`, root handlers) the way `tests/test_gunicorn_flask.py` does.

`/ready` is a readiness probe. It is excluded from request logging, so probing it adds no records.

## Tests

`tests/test_gunicorn_flask.py` starts this example with real Gunicorn on a Unix socket, waits until `/ready` answers,
sends requests with `X-Correlation-ID`, with `X-Request-ID` and with no header, stops the server, and checks the
output:

- **one worker:** application and request records carry each request's ID, the `worker ready` and `Worker exiting`
  records are JSON with `-`, `/ready` is not request-logged, and there is no Gunicorn access line;
- **two workers** (the configured count): both workers boot, log `worker ready` with their own PID, and exit with a
  JSON `Worker exiting` record; each request's ID is checked whichever worker served it;
- **access log enabled** (`--access-logfile -`): the access-line detector finds Gunicorn's lines, so the "no access
  line" check above is meaningful.

In CI (`CI=true`) a missing `gunicorn` fails the tests; elsewhere they are skipped.
