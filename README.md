# json-logging

Python logging library to emit JSON log that can be easily indexed and searchable by logging infrastructure such
as [ELK](https://www.elastic.co/elk-stack)
, [EFK](https://www.digitalocean.com/community/tutorials/how-to-set-up-an-elasticsearch-fluentd-and-kibana-efk-logging-stack-on-kubernetes)
, AWS Cloudwatch, GCP Stackdriver, etc.

If you're using Cloud Foundry, it might worth to check out the
library [SAP/cf-python-logging-support](https://github.com/SAP/cf-python-logging-support) which I'm also original
author.

# Content

1. [Features](#1-features)
2. [Usage](#2-usage)   
   2.1 [Non-web application log](#21-non-web-application-log)  
   2.2 [Web application log](#22-web-application-log)  
   2.3 [Get current correlation-id](#23-get-current-correlation-id)  
   2.4 [Log extra properties](#24-log-extra-properties)  
   2.5 [Root logger](#25-root-logger)  
   2.6 [Custom log formatter](#26-custom-log-formatter)  
   2.7 [Exclude certain URL from request instrumentation](#27-exclude-certain-url-from-request-instrumentation)
3. [Configuration](#3-configuration)
4. [Python References](#4-python-references)
5. [Framework support plugin development](#5-framework-support-plugin-development)
6. [FAQ & Troubleshooting](#6-faq--troubleshooting)
7. [References](#7-references)

# 1. Features

1. Emit JSON logs ([format detail](#0-full-logging-format-references))
2. Lightweight, no dependencies, minimal configuration needed (1 LoC to get it working)
3. Seamlessly integrate with Python native **logging** module. Support both Python 2.7.x and 3.x
4. Auto extract **correlation-id** for distributed tracing [\[1\]](#1-what-is-correlation-idrequest-id)
5. Support HTTP request instrumentation. Built in support for [FastAPI](https://fastapi.tiangolo.com/)
   , [Flask](https://github.com/pallets/flask/), [Sanic](https://github.com/channelcat/sanic)
   , [Quart](https://gitlab.com/pgjones/quart), [Connexion](https://github.com/zalando/connexion). Extensible to support
   other web frameworks. PR welcome :smiley: .
6. Highly customizable: support inject arbitrary extra properties to JSON log message, override logging formatter, etc.
7. Production ready, has been used in production since 2017 with more than 8 millions downloads

# 2. Usage

Install by running this command:
> pip install json-logging

By default log will be emitted in normal format to ease the local development. To enable it on production set enable_json in **json_logging.init_< framework_name >()** method call.
Once configured library will try to configure all loggers (existing and newly created) to emit log in JSON format. See following use cases for more detail.

## 2.1 Non-web application log

This mode don't support **correlation-id**.

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

### FastAPI

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

### Flask

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

### Sanic

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

### Quart

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

### Connexion

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

### Custom handler for request instrumentation

you need to explicitly set JSONRequestLogFormatter as default formatter for any extra handler that is added to
request_logger

```python
import json_logging.formatters

request_logger = json_logging.get_request_logger()
handler = logging.handlers.RotatingFileHandler(filename='log_req.log', maxBytes=5000000, backupCount=10)
handler.setFormatter(json_logging.formatters.JSONRequestLogFormatter())
request_logger.addHandler(handler)
```

## 2.3 Get current correlation-id

Current request correlation-id can be retrieved and pass to downstream services call as follow:

```python
# this will be faster
correlation_id = json_logging.get_correlation_id(request=request)
# this will be slower, but will work in context where you couldn't get a reference of request object
correlation_id_without_request_obj = json_logging.get_correlation_id()
# use correlation id for upstream service calls here
```

In request context, if one is not present, a new one might be generated depends on CREATE_CORRELATION_ID_IF_NOT_EXISTS
setting value.


## 2.4 Log extra properties

Extra property can be added to logging statement as follows:

```python
logger.info("test log statement", extra={'props': {'extra_property': 'extra_value'}, 'tags': ['app:name']})
```

_For backwards compatibility, properties added in `props` are extracted to the root and take precedence over those set directly in the root of `extra`. This is relevant only for logs formatted by `JSONLogFormatter`, other formatters never printed the `props` details._

### Forced overriding correlation-id
A custom correlation id can be passed to logging statement as follow:
```
logger.info("test log statement", extra={'props': {'correlation_id': 'custom_correlation_id'}})
```

## 2.5 Root logger

If you want to use root logger as main logger to emit log. Made sure you call **config_root_logger()** after initialize
root logger (by logging.basicConfig() or logging.getLogger()) [\[2\]](#2-python-logging-propagate)

```python
logging.basicConfig()
json_logging.init_ < framework_name > ()
json_logging.config_root_logger()
```

## 2.6 Custom log formatter

Customer JSON log formatter can be passed to init method. see examples for more
detail: [non web](https://github.com/thangbn/json-logging-python/blob/master/example/custom_log_format.py),
[web](https://github.com/thangbn/json-logging-python/blob/master/example/custom_log_format_request.py)

## 2.7 Exclude certain URl from request instrumentation

Certain URL can be excluded from request instrumentation by specifying a list of regex into **init_request_instrument**
method like below:

```python
json_logging.init_request_instrument(app, exclude_url_patterns=[r'/exclude_from_request_instrumentation'])
```

# 3. Configuration

logging library can be configured by setting the value in json_logging, all configuration must be placed before
json_logging.init method call

Name | Description | Default value
 --- | --- | ---
ENABLE_JSON_LOGGING | **
DEPRECATED** Whether to enable JSON logging mode.Can be set as an environment variable, enable when set to to either one in following list (case-insensitive) **['true', '1', 'y', 'yes']** , this have no effect on request logger | false
CORRELATION_ID_HEADERS | List of HTTP headers that will be used to look for correlation-id value. HTTP headers will be searched one by one according to list order| ['X-Correlation-ID','X-Request-ID']
EMPTY_VALUE | Default value when a logging record property is None |  '-'
CORRELATION_ID_GENERATOR | function to generate unique correlation-id | uuid.uuid1
JSON_SERIALIZER | function to encode object to JSON | json.dumps
COMPONENT_ID | Uniquely identifies the software component that has processed the current request | EMPTY_VALUE
COMPONENT_NAME | A human-friendly name representing the software component | EMPTY_VALUE
COMPONENT_INSTANCE_INDEX | Instance's index of horizontally scaled service | 0
CREATE_CORRELATION_ID_IF_NOT_EXISTS |  Whether to generate a new correlation-id in case one is not present| True

# 4. Python References

TODO: update Python API docs on Github page

# 5. Framework support plugin development

To add support for a new web framework, you need to extend following classes in [**
framework_base**](/blob/master/json_logging/framework_base.py) and register support using [**
json_logging.register_framework_support**](https://github.com/thangbn/json-logging-python/blob/master/json_logging/__init__.py#L38)
method:

Class | Description | Mandatory
--- | --- | ---
BaseRequestInfoExtractor | Helper class help to extract logging-relevant information from HTTP request object | yes
BaseResponseInfoExtractor | Helper class help to extract logging-relevant information from HTTP response object | yes
BaseFrameworkConfigurator |  Class to perform logging configuration for given framework as needed | no
BaseAppRequestInstrumentationConfigurator | Class to perform request instrumentation logging configuration | no

Take a look at [**json_logging/base_framework.py**](json_logging/framework_base.py), [**
json_logging.flask**](json_logging/framework/flask) and [**json_logging.sanic**](json_logging/framework/sanic) packages
for reference implementations.

# 6. FAQ & Troubleshooting

1. I configured everything, but no logs are printed out?

    - Forgot to add handlers to your logger?
    - Check whether logger is disabled.

2. Same log statement is printed out multiple times.

    - Check whether the same handler is added to both parent and child loggers [2]
    - If you using flask, by default option **use_reloader** is set to **True** which will start 2 instances of web
      application. change it to False to disable this behaviour [\[3\]](#3-more-on-flask-use-reloader)

# 7. References

## [0] Full logging format references

2 types of logging statement will be emitted by this library:

- Application log: normal logging statement e.g.:

```
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
	"line_no": 22,
	"filename": "/path/to/foo.py"
	"exc_info": "Traceback (most recent call last): \n  File "<stdin>", line 1, in <module>\n ValueError: There is something wrong with your input",
	"correlation_id": "1975a02e-e802-11e7-8971-28b2bd90b19a",
	"extra_property": "extra_value",
	"msg": "This is a message"
}
```

- Request log: request instrumentation logging statement which recorded request information such as response time,
  request size, etc.

```
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

See following tables for detail format explanation:

- Common field

Field | Description | Format | Example
 --- | --- | --- | ---
written_at | The date when this log message was written. | ISO 8601 YYYY-MM-DDTHH:MM:SS.milliZ | 2017-12-23T15:14:02.208Z
written_ts | The timestamp in nano-second precision when this request metric message was written. | long number | 1456820553816849408
correlation_id | The timestamp in nano-second precision when this request metric message was written. | string | db2d002e-2702-41ec-66f5-c002a80a3d3f
type | Type of logging. "logs" or "request"  | string |
component_id | Uniquely identifies the software component that has processed the current request | string | 9e6f3ecf-def0-4baf-8fac-9339e61d5645
component_name | A human-friendly name representing the software component | string | my-fancy-component
component_instance_idx | Instance's index of horizontally scaled service  | string | 0

- application logs

Field | Description | Format | Example
 --- | --- | --- | ---
msg | The actual message string passed to the logger.  | string | This is a log message
level | The log "level" indicating the severity of the log message.  | string | INFO
thread | Identifies the execution thread in which this log message has been written.  | string | http-nio-4655
logger | The logger name that emits the log message. |string | requests-logger
filename | The file name where an exception originated | string | /path/to/foo.py
exc_info | Traceback information about an exception | string | "Traceback (most recent call last): \n  File "<stdin>", line 1, in <module>\n ValueError: There is something wrong with your input"

- request logs:

Field | Description | Format | Example
 --- | --- | --- | ---
request | request path that has been processed. | string | /get/api/v2
request_received_at | The date when an incoming request was received by the producer.| ISO 8601 YYYY-MM-DDTHH:MM:SS.milliZ   The precision is in milliseconds. The timezone is UTC.  | 2015-01-24 14:06:05.071Z
response_sent_at | The date when the response to an incoming request was sent to the consumer.  | ditto | 2015-01-24 14:06:05.071Z
response_time_ms | How many milliseconds it took the producer to prepare the response.  | float | 43.476
protocol | Which protocol was used to issue a request to a producer. In most cases, this will be HTTP (including a version specifier), but for outgoing requests reported by a producer, it may contain other values. E.g. a database call via JDBC may report, e.g. "JDBC/1.2"  | string | HTTP/1.1
method | The corresponding protocol method. | string | GET
remote_ip |  IP address of the consumer (might be a proxy, might be the actual client) | string | 192.168.0.1
remote_host |  host name of the consumer (might be a proxy, might be the actual client) | string | my.happy.host
remote_port | Which TCP port is used by the consumer to establish a connection to the remote producer. | string | 1234
remote_user | The username associated with the request | string | user_name
request_size_b | The size in bytes of the requesting entity or "body" (e.g., in case of POST requests). | long | 1234
response_size_b | The size in bytes of the response entity | long | 1234
response_status | The status code of the response. | long | 200
response_content_type | The MIME type associated with the entity of the response if available/specified | long | application/json
referer | For HTTP requests, identifies the address of the webpage (i.e. the URI or IRI) that linked to the resource being requested. | string |  /index.html
x_forwarded_for | Comma-separated list of IP addresses, the left-most being the original client, followed by proxy server addresses that forwarded the client request. | string |  192.0.2.60,10.12.9.23

## [1] What is correlation-id/request id

https://stackoverflow.com/questions/25433258/what-is-the-x-request-id-http-header

## [2] Python logging propagate

https://docs.python.org/3/library/logging.html#logging.Logger.propagate
https://docs.python.org/2/library/logging.html#logging.Logger.propagate

## [3] more on flask use_reloader

http://flask.pocoo.org/docs/0.12/errorhandling/#working-with-debuggers
