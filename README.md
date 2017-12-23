# json-logging
Python logging library to emit JSON log that can be easily indexed and searchable by logging infrastructure such as [ELK](https://www.elastic.co/webinars/introduction-elk-stack).  
If you're using Cloud Foundry, it worth to check out the library [SAP/cf-python-logging-support](https://github.com/SAP/cf-python-logging-support) which I'm also original author and contributor.
# Content
1. [Features](#1-features)
2. [Usage](#2-usage)   
   2.1 [Non-web application log](#21-non-web-application-log)  
   2.2 [Web application log](#22-web-application-log)  
   2.3 [Get current correlation-id](#23-get-current-correlation-id)  
   2.4 [Log extra properties](#24-log-extra-properties)  
   2.5 [Root logger](#25-root-logger)
3. [Configuration](#3-configuration)  
4. [Python References](#4-python-references)
5. [Framework support plugin development](#5-framework-support-plugin-development)
6. [FAQ & Troubleshooting](#6-faq--troubleshooting)
7. [References](#7-references)

# 1. Features
1. Lightweight, no dependencies. Tested with Python 2.7 & 3.5.
2. 100% compatible with **logging** module. Minimal configuration needed.
3. Emit JSON logs [\[0\]](#0-full-logging-format-references) 
4. Support **correlation-id** [\[1\]](#1-what-is-correlation-idrequest-id)
5. Support request instrumentation. Built in support for [Flask](http://flask.pocoo.org/) & [Sanic](http://flask.pocoo.org/). Extensible to support others.
6. Support adding extra properties to JSON log object.

# 2. Usage
This library is very intrusive, once configured library will try to configure all loggers (existing and newly created) to emit log in JSON format.
Install by running this command:
   > pip install json-logging  
   
The most important method is **init(framework_name)**.

TODO: update guide on how to use ELK stack to view log

## 2.1 Non-web application log
This mode don't support **correlation-id**.
```python
import json_logging, logging, sys

# log is initialized without a web framework name
json_logging.init()

logger = logging.getLogger("test-logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

logger.info("test logging statement")
```

## 2.2 Web application log
### Flask

```python
import datetime, logging, sys, json_logging, flask

app = flask.Flask(__name__)
json_logging.init(framework_name='flask')
json_logging.init_request_instrument(app)

# init the logger as usual
logger = logging.getLogger("test-logger")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

@app.route('/')
def home():
    logger.info("test log statement")
    return "Hello world : " + str(datetime.datetime.now())

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(5000), use_reloader=False)
```

### Sanic
```python
import logging, sys, json_logging, sanic

app = sanic.Sanic()
json_logging.init(framework_name='sanic')
json_logging.init_request_instrument(app)

# init the logger as usual
logger = logging.getLogger("sanic-integration-test-app")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

@app.route("/")
async def home(request):
    logger.info("test log statement")
    return sanic.response.text("hello world")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

## 2.3 Get current correlation-id
Current request correlation-id can be retrieved and pass to downstream services call as follow:

```python
correlation_id = json_logging.get_correlation_id()
# use correlation id for downstream service calls here
```

In request context, if one is not present, a new one might be generated depends on CREATE_CORRELATION_ID_IF_NOT_EXISTS setting value.

## 2.4 Log extra properties
Extra property can be added to logging statement as follow:
```python
logger.info("test log statement", extra = {'props' : {'extra_property' : 'extra_value'}})
```
## 2.5 Root logger
If you want to use root logger as main logger to emit log. Made sure you call **config_root_logger()** after initialize root logger (by
logging.basicConfig() or logging.getLogger('root')) [\[2\]](#2-python-logging-propagate)
```python
logging.basicConfig()
json_logging.config_root_logger()
```

# 3. Configuration
logging library can be configured by setting the value in json_logging

Name | Description | Default value
 --- | --- | ---
ENABLE_JSON_LOGGING | Whether to enable JSON logging mode.Can be set as an environment variable, enable when set to to either one in following list (case-insensitive) **['true', '1', 'y', 'yes']** | false
ENABLE_JSON_LOGGING_DEBUG |  Whether to enable debug logging for this library for development purpose. | true
CORRELATION_ID_HEADERS | List of HTTP headers that will be used to look for correlation-id value. HTTP headers will be searched one by one according to list order| ['X-Correlation-ID','X-Request-ID']
EMPTY_VALUE | Default value when a logging record property is None |  '-'
CORRELATION_ID_GENERATOR | function to generate unique correlation-id | uuid.uuid1
JSON_SERIALIZER | function to encode object to JSON | json.dumps
COMPONENT_ID | Uniquely identifies the software component that has processed the current
request | EMPTY_VALUE
COMPONENT_NAME | A human-friendly name representing the software component | EMPTY_VALUE
COMPONENT_INSTANCE_INDEX | Instance's index of horizontally scaled service | 0
CREATE_CORRELATION_ID_IF_NOT_EXISTS |  Whether to generate an new correlation-id in case one is not present| True

# 4. Python References

TODO: update Python API docs on Github page

# 5. Framework support plugin development
To add support for a new web framework, you need to extend following classes in [**framework_base**](/blob/master/json_logging/framework_base.py) and register support using [**json_logging.register_framework_support**](https://github.com/thangbn/json-logging-python/blob/master/json_logging/__init__.py#L38) method:

Class | Description | Mandatory
--- | --- | ---
RequestAdapter | Helper class help to extract logging-relevant information from HTTP request object | no
ResponseAdapter | Helper class help to extract logging-relevant information from HTTP response object | yes
FrameworkConfigurator |  Class to perform logging configuration for given framework as needed | no
AppRequestInstrumentationConfigurator | Class to perform request instrumentation logging configuration | no

Take a look at [**json_logging/base_framework.py**](blob/master/json_logging/framework_base.py), [**json_logging.flask**](tree/master/json_logging/framework/flask) and [**json_logging.sanic**](/tree/master/json_logging/framework/sanic) packages for reference implementations.

# 6. FAQ & Troubleshooting
1. I configured everything, but no logs are printed out?

    - Forgot to add handlers to your logger?
    - Check whether logger is disabled.

2. Same log statement is printed out multiple times.

    - Check whether the same handler is added to both parent and child loggers [2]
    - If you using flask, by default option **use_reloader** is set to **True** which will start 2 instances of web application. change it to False to disable this behaviour [\[3\]](#3-more-on-flask-use-reloader)
3.  Can not install Sanic on Windows?

you can install Sanic on windows by running these commands:
```
git clone --branch 0.7.0 https://github.com/channelcat/sanic.git
set SANIC_NO_UVLOOP=true
set SANIC_NO_UJSON=true
pip3 install .
```
# 7. References
## [0] Full logging format references
- Common field
Field | Description | Format | Example
 --- | --- | --- | ---
written_at | The date when this log message was written. | ISO 8601 YYYY-MM-DDTHH:MM:SS.milliZ | 2017-12-23T15:14:02.208Z 
written_ts | The timestamp in nano-second precision when this request metric message was written. | long number | 1456820553816849408
correlation_id | The timestamp in nano-second precision when this request metric message was written. | string | db2d002e-2702-41ec-66f5-c002a80a3d3f
type | Type of message. "logs" or "request"  | string | db2d002e-2702-41ec-66f5-c002a80a3d3f
component_id | Uniquely identifies the software component that has processed the current
request | string | 9e6f3ecf-def0-4baf-8fac-9339e61d5645
component_name | A human-friendly name representing the software component | string | my-fancy-component 
component_instance | Instance's index of horizontally scaled service  | string | 0

- application logs:  https://github.com/SAP/cf-java-logging-support/blob/master/cf-java-logging-support-core/beats/app-logs/docs/fields.asciidoc#exported-fields-app-logs
Field | Description | Format | Example
 --- | --- | --- | ---
msg | The actual message string passed to the logger.  | string | This is a log message
level | The log "level" indicating the severity of the log message.  | string | INFO
thread | Identifies the execution thread in which this log message has been written.  | string | http-nio-4655
logger | The logger name that emits the log message.
 | string | requests-logger

- request logs: 
Field | Description | Format | Example
 --- | --- | --- | ---
request | request path  that has been processed. | string | /get/api/v2
request_received_at | The date when an incoming request was received by the producer.| ISO 8601 YYYY-MM-DDTHH:MM:SS.milliZ   The precision is in milliseconds. The timezone is UTC.  | 2015-01-24 14:06:05.071Z
response_sent_at | The date when the response to an incoming request was sent to the consumer.  | ditto | 2015-01-24 14:06:05.071Z
response_time_ms | How many milliseconds it took the producer to prepare the response.  | float | 43.476
protocol | Which protocol was used to issue a request to a producer. In most cases, this will be HTTP (including a version specifier), but for outgoing requests reported by a producer it may contain other values. E.g. a database call via JDBC may report, e.g. "JDBC/1.2"  | string | HTTP/1.1
method | The corresponding protocol method. | string | GET
remote_ip |  IP address of the consumer (might be a proxy, might be the actual client) | string | 192.168.0.1
remote_host |  host name of the consumer (might be a proxy, might be the actual client) | string | my.happy.host
remote_port | Which TCP port is used by the consumer to establish a connection to the remote producer. | string | 1234
remote_user | The username associated with the request | string | user_name
request_size_b | The size in bytes of the request entity or "body" (e.g., in case of POST requests). | long | 1234
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