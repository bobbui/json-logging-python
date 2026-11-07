# json-logging

[![PyPI version](https://img.shields.io/pypi/v/json-logging)](https://pypi.org/project/json-logging/)
[![Python versions](https://img.shields.io/pypi/pyversions/json-logging)](https://pypi.org/project/json-logging/)
[![Downloads](https://static.pepy.tech/badge/json-logging)](https://pepy.tech/project/json-logging)
[![Code Quality](https://github.com/bobbui/json-logging-python/actions/workflows/code_quality.yml/badge.svg)](https://github.com/bobbui/json-logging-python/actions/workflows/code_quality.yml)
[![License](https://img.shields.io/pypi/l/json-logging)](LICENSE)

Python logging library that emits JSON logs, ready to be indexed and searched by logging infrastructure such as
[ELK](https://www.elastic.co/elastic-stack),
[EFK](https://www.digitalocean.com/community/tutorials/how-to-set-up-an-elasticsearch-fluentd-and-kibana-efk-logging-stack-on-kubernetes),
AWS CloudWatch, Google Cloud Logging, etc.

If you're using Cloud Foundry, also take a look at
[SAP/cf-python-logging-support](https://github.com/SAP/cf-python-logging-support), which was written by the original
author of this library.

## Quickstart

```bash
pip install json-logging
```

```python
import json_logging, logging, sys

json_logging.init_non_web(enable_json=True)

logger = logging.getLogger("my-app")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

logger.info("hello from json-logging", extra={"props": {"order_id": 42}})
```

Output:

```json
{"written_at": "2026-11-06T20:42:29.161Z", "written_ts": 1793997749161870000, "order_id": 42, "msg": "hello from json-logging", "type": "log", "logger": "my-app", "thread": "MainThread", "level": "INFO", "module": "app", "line_no": 8}
```

## Contents

1. [Features](#1-features)
2. [Usage](#2-usage)
   - 2.1 [Non-web application log](#21-non-web-application-log)
   - 2.2 [Web application log](#22-web-application-log)
   - 2.3 [Get current correlation-id](#23-get-current-correlation-id)
   - 2.4 [Log extra properties](#24-log-extra-properties)
   - 2.5 [Root logger](#25-root-logger)
   - 2.6 [Custom log formatter](#26-custom-log-formatter)
   - 2.7 [Exclude certain URLs from request instrumentation](#27-exclude-certain-urls-from-request-instrumentation)
   - 2.8 [Exclude fields from the JSON output](#28-exclude-fields-from-the-json-output)
3. [Configuration](#3-configuration)
4. [Framework support plugin development](#4-framework-support-plugin-development)
5. [FAQ & Troubleshooting](#5-faq--troubleshooting)
6. [Maintainers](#6-maintainers)
7. [References](#7-references)

# 1. Features

1. Emits JSON logs ([format details](#0-full-logging-format-references))
2. Lightweight, no dependencies, minimal configuration needed (1 line of code to get it working)
3. Integrates seamlessly with the Python native **logging** module. Supports both Python 2.7.x and 3.x
4. Automatically extracts the **correlation-id** for distributed tracing [\[1\]](#1-what-is-correlation-idrequest-id)
5. HTTP request instrumentation, with built-in support for the frameworks below. Extensible to support other web
   frameworks; PRs welcome :smiley:
6. Highly customizable: inject arbitrary extra properties into JSON log messages, override the logging formatter, etc.
7. Production ready: used in production since 2017

| Framework | Init function | Example |
|---|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | `json_logging.init_fastapi()` | [fastapi_sample_app.py](example/fastapi_sample_app.py), [fastapi_startup](example/fastapi_startup/README.md) |
| [Flask](https://flask.palletsprojects.com/) | `json_logging.init_flask()` | [flask_sample_app.py](example/flask_sample_app.py), [gunicorn_flask](example/gunicorn_flask/README.md) |
| [Sanic](https://sanic.dev/) | `json_logging.init_sanic()` | [sanic_sample_app.py](example/sanic_sample_app.py) |
| [Quart](https://quart.palletsprojects.com/) | `json_logging.init_quart()` | [quart_sample_app.py](example/quart_sample_app.py) |
| [Connexion](https://github.com/spec-first/connexion) | `json_logging.init_connexion()` | [connexion-example](example/connexion-example) |
| No web framework | `json_logging.init_non_web()` | [non_web.py](example/non_web.py) |

# 2. Usage

Install by running:

```bash
pip install json-logging
```

By default, logs are emitted in the normal (non-JSON) format to make local development easier. To enable JSON output
in production, pass `enable_json=True` to the `json_logging.init_<framework_name>()` call.
Once configured, the library configures all loggers (existing and newly created) to emit logs in JSON format. See the
following use cases for more details.

## 2.1 Non-web application log

This mode doesn't support **correlation-id**.

```python
import json_logging, logging, sys

# log is initialized without a web framework name
json_logging.init_non_web(enable_json=True)

logger = logging.getLogger("test-logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

logger.info("test logging statement")
```

## 2.2 Web application log

Every framework follows the same pattern: call `json_logging.init_<framework_name>(enable_json=True)`, then
`json_logging.init_request_instrument(app)`, then set up your loggers as usual. Expand a framework below for a full
example.

<details>
<summary><b>FastAPI</b></summary>

```python
import datetime, logging, sys, json_logging, fastapi, uvicorn

app = fastapi.FastAPI()
json_logging.init_fastapi(enable_json=True)
json_logging.init_request_instrument(app)

# init the logger as usual
logger = logging.getLogger("test-logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))


@app.get('/')
def home():
    logger.info("test log statement")
    logger.info("test log statement with extra props", extra={'props': {"extra_property": 'extra_value'}})
    correlation_id = json_logging.get_correlation_id()
    return "Hello world : " + str(datetime.datetime.now())


if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=5000)
```

</details>

<details>
<summary><b>Flask</b></summary>

```python
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
    app.run(host='0.0.0.0', port=int(5000), use_reloader=False)
```

</details>

<details>
<summary><b>Sanic</b></summary>

```python
import logging, sys, json_logging, sanic

app = sanic.Sanic(name="sanic-web-app")
json_logging.init_sanic(enable_json=True)
json_logging.init_request_instrument(app)

# init the logger as usual
logger = logging.getLogger("sanic-integration-test-app")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))


@app.route("/")
async def home(request):
    logger.info("test log statement")
    logger.info("test log statement with extra props", extra={'props': {"extra_property": 'extra_value'}})
    # this will be faster
    correlation_id = json_logging.get_correlation_id(request=request)
    # this will be slower, but will work in context you cant get a reference of request object
    correlation_id_without_request_obj = json_logging.get_correlation_id()

    return sanic.response.text("hello world")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

</details>

<details>
<summary><b>Quart</b></summary>

```python
import asyncio, logging, sys, json_logging, quart

app = quart.Quart(__name__)
json_logging.init_quart(enable_json=True)
json_logging.init_request_instrument(app)

# init the logger as usual
logger = logging.getLogger("test logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))


@app.route('/')
async def home():
    logger.info("test log statement")
    logger.info("test log statement with extra props", extra={'props': {"extra_property": 'extra_value'}})
    correlation_id = json_logging.get_correlation_id()
    return "Hello world"


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app.run(host='0.0.0.0', port=int(5000), use_reloader=False, loop=loop)
```

</details>

<details>
<summary><b>Connexion</b></summary>

```python
import logging, sys, json_logging, connexion

app = connexion.FlaskApp(__name__)
json_logging.init_connexion(enable_json=True)
json_logging.init_request_instrument(app)

app.add_api('api.yaml')

# init the logger as usual
logger = logging.getLogger("test-logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

if __name__ == "__main__":
    app.run()
```

With Connexion 3, `connexion.AsyncApp` is supported the same way. Requests are instrumented by an ASGI middleware
instead of Flask hooks, so call `init_request_instrument(app)` before the first ASGI call, including lifespan startup.
Connexion refuses to add middleware once the app has started. In AsyncApp request logs, `remote_user` is
`json_logging.EMPTY_VALUE` (`"-"`), because the authenticated user is only known to Connexion's security handlers:

```python
app = connexion.AsyncApp(__name__)
json_logging.init_connexion(enable_json=True)
json_logging.init_request_instrument(app)
```

</details>

### Custom handler for request instrumentation

You need to explicitly set `JSONRequestLogFormatter` as the formatter for any extra handler that is added to the
request logger:

```python
import logging.handlers
import json_logging.formatters

request_logger = json_logging.get_request_logger()
handler = logging.handlers.RotatingFileHandler(filename='log_req.log', maxBytes=5000000, backupCount=10)
handler.setFormatter(json_logging.formatters.JSONRequestLogFormatter())
request_logger.addHandler(handler)
```

## 2.3 Get current correlation-id

The current request's correlation-id can be retrieved and passed to downstream service calls as follows:

```python
# this will be faster
correlation_id = json_logging.get_correlation_id(request=request)
# this will be slower, but will work in contexts where you can't get a reference to the request object
correlation_id_without_request_obj = json_logging.get_correlation_id()
# use correlation id for upstream service calls here
```

In a request context, if no correlation-id is present, a new one may be generated, depending on the
`CREATE_CORRELATION_ID_IF_NOT_EXISTS` setting.

Before initialization or after `init_non_web()`, `json_logging.get_correlation_id()` returns
`json_logging.EMPTY_VALUE` (`"-"`) instead of raising an error or generating an HTTP correlation ID.

## 2.4 Log extra properties

Extra properties can be added to a logging statement as follows:

```python
logger.info("test log statement", extra={'props': {'extra_property': 'extra_value'}, 'tags': ['app:name']})
```

_For backwards compatibility, properties added in `props` are extracted to the root and take precedence over those set directly in the root of `extra`. This is relevant only for logs formatted by `JSONLogFormatter`, other formatters never printed the `props` details._

### Forced overriding correlation-id

A custom correlation-id can be passed to a logging statement as follows:

```python
logger.info("test log statement", extra={'props': {'correlation_id': 'custom_correlation_id'}})
```

## 2.5 Root logger

If you want to use the root logger as the main logger to emit logs, make sure you call `config_root_logger()` after
initializing the root logger (by `logging.basicConfig()` or `logging.getLogger()`)
[\[2\]](#2-python-logging-propagate):

```python
logging.basicConfig()
json_logging.init_flask(enable_json=True)  # or the init_<framework_name>() call for your framework
json_logging.config_root_logger()
```

## 2.6 Custom log formatter

A custom JSON log formatter can be passed to the init method. See the examples for more details:
[non-web](example/custom_log_format.py), [web](example/custom_log_format_request.py).

## 2.7 Exclude certain URLs from request instrumentation

Certain URLs can be excluded from request instrumentation by passing a list of regular expressions to
`init_request_instrument()`:

```python
json_logging.init_request_instrument(app, exclude_url_patterns=[r'/exclude_from_request_instrumentation'])
```

## 2.8 Exclude fields from the JSON output

Set `json_logging.EXCLUDED_FIELDS` to omit fields from every JSON record, including request logs:

```python
import json_logging

json_logging.EXCLUDED_FIELDS = ["written_ts"]          # or a tuple/set/frozenset of field names
json_logging.init_flask(enable_json=True)
```

- The default is `()`, so output is unchanged.
- Set it **before** calling `init_*()`: formatters read it when they are constructed, the same way as `COMPONENT_*`.
- A bare string, or a collection containing non-strings, raises `TypeError` from `init_*()`,
  `init_request_instrument()` or a formatter constructor. The `init_*()` and `init_request_instrument()` calls
  validate the setting before changing any state, so you can correct it and call them again.
- Fields are removed after they are collected, so `extra` and `props` entries are removed too.
- Exclusions apply to formatters that use `BaseJSONFormatter.format()`: the built-in JSON formatters and subclasses
  that inherit or call it. A custom `logging.Formatter` that does not use it must filter fields itself.
- Excluding a field changes the JSON schema. Downstream log consumers may depend on fields such as `written_ts`,
  `correlation_id` or `level`; exclude a field only when you know nothing downstream reads it.
- This is an output-formatting option, **not** a security redaction or data-loss-prevention control. A sensitive
  value can still appear in the message, in another field, or through another handler or formatter.

# 3. Configuration

The library is configured by setting attributes on the `json_logging` module. All configuration must be done before
the `json_logging.init_<framework_name>()` call:

```python
import json_logging

json_logging.CORRELATION_ID_HEADERS = ["X-Request-ID"]
json_logging.COMPONENT_NAME = "orders-service"
json_logging.init_fastapi(enable_json=True)
```

| Name | Description | Default value |
|---|---|---|
| `ENABLE_JSON_LOGGING` | **Deprecated.** Whether to enable JSON logging mode. Can be set as an environment variable; enabled when set to any of **`true`, `1`, `y`, `yes`** (case-insensitive). Has no effect on the request logger. | `false` |
| `CORRELATION_ID_FIELD` | Name of the field in generated log messages that contains the correlation-id value | `'correlation_id'` |
| `CORRELATION_ID_HEADERS` | List of HTTP headers used to look up the correlation-id value. Headers are searched one by one, in list order. | `['X-Correlation-ID', 'X-Request-ID']` |
| `EMPTY_VALUE` | Default value when a logging record property is `None` | `'-'` |
| `CORRELATION_ID_GENERATOR` | Function that generates a unique correlation-id | `uuid.uuid1` |
| `JSON_SERIALIZER` | Function that encodes an object to JSON | `json.dumps` |
| `COMPONENT_ID` | Uniquely identifies the software component that has processed the current request | `EMPTY_VALUE` |
| `COMPONENT_NAME` | A human-friendly name representing the software component | `EMPTY_VALUE` |
| `COMPONENT_INSTANCE_INDEX` | Instance index of a horizontally scaled service | `0` |
| `CREATE_CORRELATION_ID_IF_NOT_EXISTS` | Whether to generate a new correlation-id when one is not present | `True` |

# 4. Framework support plugin development

To add support for a new web framework, extend the following classes in
[`json_logging/framework_base.py`](json_logging/framework_base.py) and register support using the
[`json_logging.frameworks.register_framework_support()`](json_logging/frameworks.py) method:

| Class | Description | Mandatory |
|---|---|---|
| `BaseRequestInfoExtractor` | Helper class to extract logging-relevant information from the HTTP request object | yes |
| `BaseResponseInfoExtractor` | Helper class to extract logging-relevant information from the HTTP response object | yes |
| `BaseFrameworkConfigurator` | Class to perform logging configuration for the given framework as needed | no |
| `BaseAppRequestInstrumentationConfigurator` | Class to perform request instrumentation logging configuration | no |

Take a look at [`json_logging/framework_base.py`](json_logging/framework_base.py) and the
[`json_logging.framework.flask`](json_logging/framework/flask) and
[`json_logging.framework.sanic`](json_logging/framework/sanic) packages for reference implementations.

# 5. FAQ & Troubleshooting

1. I configured everything, but no logs are printed out?

    - Did you forget to add handlers to your logger?
    - Check whether the logger is disabled.

2. The same log statement is printed out multiple times.

    - Check whether the same handler is added to both parent and child loggers
      [\[2\]](#2-python-logging-propagate)
    - If you're using Flask, the **use_reloader** option defaults to **True**, which starts 2 instances of the web
      application. Set it to `False` to disable this behavior [\[3\]](#3-more-on-flask-use_reloader)

3. `RuntimeError: Can not call init more than once` with FastAPI.

    - The module that calls `init_fastapi()` ran twice, for example when it is started as a script and uvicorn
      also imports it by an import string such as `"app.main:app"`. Start uvicorn with
      `python -m uvicorn app.main:app`, or pass the app object to `uvicorn.run(app)`. See
      [example/fastapi_startup](example/fastapi_startup/README.md).

# 6. Maintainers

The maintainers support the ongoing engineering development, quality, compatibility, and sustainability of
`json-logging`. See [MAINTAINERS.md](MAINTAINERS.md) for maintainer details, [MAINTENANCE.md](MAINTENANCE.md) for
project procedures, and [AGENTS.md](AGENTS.md) for coding-agent guidance.

### Technical Maintainers

| Name | GitHub | Affiliation |
|---|---|---|
| Udit Agrawal | [@suppagoddo](https://github.com/suppagoddo) | Apple Inc |
| Srinivas Chippagiri | [@cvas22](https://github.com/cvas22) | Salesforce Inc |

### Emeritus Maintainers

| Name | GitHub |
|---|---|
| Bob T. | [@bobbui](https://github.com/bobbui) |

# 7. References

## [0] Full logging format references

This library emits 2 types of log records:

- Application log: a normal logging statement, e.g.:

```json
{
  "type": "log",
  "written_at": "2017-12-23T16:55:37.280Z",
  "written_ts": 1514048137280721000,
  "component_id": "1d930c0xd-19-s3213",
  "component_name": "ny-component_name",
  "component_instance_idx": 0,
  "logger": "test logger",
  "thread": "MainThread",
  "level": "INFO",
  "module": "foo",
  "line_no": 22,
  "filename": "/path/to/foo.py",
  "exc_info": "Traceback (most recent call last): \n  File \"<stdin>\", line 1, in <module>\n ValueError: There is something wrong with your input",
  "correlation_id": "1975a02e-e802-11e7-8971-28b2bd90b19a",
  "extra_property": "extra_value",
  "msg": "This is a message"
}
```

- Request log: a request instrumentation record with request information such as response time, request size, etc.

```json
{
  "type": "request",
  "written_at": "2017-12-23T16:55:37.280Z",
  "written_ts": 1514048137280721000,
  "component_id": "-",
  "component_name": "-",
  "component_instance_idx": 0,
  "correlation_id": "1975a02e-e802-11e7-8971-28b2bd90b19a",
  "remote_user": "user_a",
  "request": "/index.html",
  "referer": "-",
  "x_forwarded_for": "-",
  "protocol": "HTTP/1.1",
  "method": "GET",
  "remote_ip": "127.0.0.1",
  "request_size_b": 1234,
  "remote_host": "127.0.0.1",
  "remote_port": 50160,
  "request_received_at": "2017-12-23T16:55:37.280Z",
  "response_time_ms": 0,
  "response_status": 200,
  "response_size_b": "122",
  "response_content_type": "text/html; charset=utf-8",
  "response_sent_at": "2017-12-23T16:55:37.280Z"
}
```

See the following tables for a detailed explanation of the format:

**Common fields**

| Field | Description | Format | Example |
|---|---|---|---|
| written_at | The date when this log message was written. | ISO 8601 YYYY-MM-DDTHH:MM:SS.milliZ | 2017-12-23T15:14:02.208Z |
| written_ts | The timestamp in nanosecond precision when this log message was written. | long number | 1456820553816849408 |
| correlation_id | The correlation-id of the request this log message belongs to. Present in web application logs. | string | db2d002e-2702-41ec-66f5-c002a80a3d3f |
| type | Type of logging: "log" or "request" | string | log |
| component_id | Uniquely identifies the software component that has processed the current request | string | 9e6f3ecf-def0-4baf-8fac-9339e61d5645 |
| component_name | A human-friendly name representing the software component | string | my-fancy-component |
| component_instance_idx | Instance index of a horizontally scaled service | string | 0 |

**Application logs**

| Field | Description | Format | Example |
|---|---|---|---|
| msg | The actual message string passed to the logger. | string | This is a log message |
| level | The log "level" indicating the severity of the log message. | string | INFO |
| thread | Identifies the execution thread in which this log message has been written. | string | http-nio-4655 |
| logger | The name of the logger that emitted the log message. | string | requests-logger |
| module | The module name of the logging call | string | foo |
| line_no | The line number of the logging call | integer | 22 |
| filename | The file where an exception originated, only present when an exception is logged | string | /path/to/foo.py |
| exc_info | Traceback information about an exception | string | "Traceback (most recent call last): \n  File "&lt;stdin&gt;", line 1, in &lt;module&gt;\n ValueError: There is something wrong with your input" |
| stack_info | Call stack of the logging statement, only present when it was called with `stack_info=True` | string | "Stack (most recent call last):\n  File "app.py", line 10, in &lt;module&gt;\n    logger.info("hello", stack_info=True)" |

**Request logs**

| Field | Description | Format | Example |
|---|---|---|---|
| request | Request path that has been processed. | string | /get/api/v2 |
| request_received_at | The date when an incoming request was received by the producer. | ISO 8601 YYYY-MM-DDTHH:MM:SS.milliZ. The precision is in milliseconds. The timezone is UTC. | 2015-01-24T14:06:05.071Z |
| response_sent_at | The date when the response to an incoming request was sent to the consumer. | ditto | 2015-01-24T14:06:05.071Z |
| response_time_ms | How many milliseconds it took the producer to prepare the response. | integer | 43 |
| protocol | Which protocol was used to issue a request to a producer. In most cases, this will be HTTP (including a version specifier), but for outgoing requests reported by a producer, it may contain other values, e.g. a database call via JDBC may report "JDBC/1.2". | string | HTTP/1.1 |
| method | The corresponding protocol method. | string | GET |
| remote_ip | IP address of the consumer (might be a proxy, might be the actual client) | string | 192.168.0.1 |
| remote_host | Host name of the consumer (might be a proxy, might be the actual client) | string | my.happy.host |
| remote_port | Which TCP port is used by the consumer to establish a connection to the remote producer. | integer | 1234 |
| remote_user | The username associated with the request | string | user_name |
| request_size_b | The size in bytes of the requesting entity or "body" (e.g., in case of POST requests). | long | 1234 |
| response_size_b | The size in bytes of the response entity | long | 1234 |
| response_status | The status code of the response. | long | 200 |
| response_content_type | The MIME type associated with the entity of the response if available/specified | string | application/json |
| referer | For HTTP requests, identifies the address of the webpage (i.e. the URI or IRI) that linked to the resource being requested. | string | /index.html |
| x_forwarded_for | Comma-separated list of IP addresses, the left-most being the original client, followed by proxy server addresses that forwarded the client request. | string | 192.0.2.60,10.12.9.23 |

## [1] What is correlation-id/request id

[What is the X-Request-ID HTTP header?](https://stackoverflow.com/questions/25433258/what-is-the-x-request-id-http-header)
(Stack Overflow)

## [2] Python logging propagate

[`Logger.propagate`](https://docs.python.org/3/library/logging.html#logging.Logger.propagate) in the Python
documentation

## [3] More on Flask use_reloader

[Debugging application errors](https://flask.palletsprojects.com/en/stable/debugging/) in the Flask documentation
