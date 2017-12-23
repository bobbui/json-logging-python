# json-logging
Python logging library to emit JSON log that can be easily indexed and searchable by logging infrastructure such as [ELK](https://www.elastic.co/webinars/introduction-elk-stack).  
If you're using Cloud Foundry, it worth to check out this library [cf-python-logging-support](https://github.com/SAP/cf-python-logging-support) which I'm also original author and contributor.
# Content
1. [Features](#1-features)
2. [Installation](#2-installation)
3. [Usage](#3-usage)   
   3.1 [Non-web application log](#311-non-web-application-log)  
   3.2 [Web application log](#312-web-application-log)  
   3.3 [Get current correlation-id](#321-get-current-correlation-id)  
   3.4 [Log extra properties](#322-log-extra-properties)  
   3.5 [Root logger](#323-root-logger)
4. [Configuration](#4-configuration)  
5. [Python References](#5-python-references)
6. [Framework support plugin development](#6-framework-support-plugin-development)
7. [FAQ & Troubleshooting](#7-faq--troubleshooting)
8. [References](#8-references)

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

TODO: using ELK stack to view log

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
**logging.basicConfig()** or **logging.getLogger('root')**) [\[2\]](#2-python-logging-propagate)
```python
logging.basicConfig()
json_logging.config_root_logger()
```

# 4. Configuration
logging library can be configured by setting the value in json_logging
Name | Description | Default value
 --- | --- | ---
ENABLE_JSON_LOGGING | Whether to enable JSON logging mode.Can be set as an environment variable, enable when set to to either one in following list (case-insensitive) **['true', '1', 'y', 'yes']** | false
ENABLE_JSON_LOGGING_DEBUG |  Whether to enable debug logging for this library for development purpose. | true
CORRELATION_ID_HEADERS | List of HTTP headers that will be used to look for correlation-id value. HTTP headers will be searched one by one according to list order| ['X-Correlation-ID','X-Request-ID']
EMPTY_VALUE | Default value when a logging record property is None |  '-'
CORRELATION_ID_GENERATOR | function to generate unique correlation-id | uuid.uuid1
JSON_SERIALIZER | function to encode object to JSON | json.dumps
LAYER | The execution layer in the component that emitted the message | 'python'
COMPONENT_TYPE | A human-friendly name representing the software component |
CREATE_CORRELATION_ID_IF_NOT_EXISTS |  Whether to generate an new correlation-id in case one is not present.| True

# 5. Python References

TODO: update Python API docs on Github page

# 6. Framework support plugin development

To add support for a new web framework, you need to extend following classes in **framework_base** and register support using **register_framework_support** method:

Class | Description | Mandatory
--- | --- | ---
RequestAdapter | Helper class help to extract logging-relevant information from HTTP request object | no
ResponseAdapter | Helper class help to extract logging-relevant information from HTTP response object | yes
FrameworkConfigurator |  Class to perform logging configuration for given framework as needed | no
AppRequestInstrumentationConfigurator | Class to perform request instrumentation logging configuration | no

Take a look at **json_logging/base_framework.py**, **json_logging.flask** and **json_logging.sanic** packages for reference implementations

# 7. FAQ & Troubleshooting
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
# 8. References
## [0] Full logging format references
- application logs:  https://github.com/SAP/cf-java-logging-support/blob/master/cf-java-logging-support-core/beats/app-logs/docs/fields.asciidoc#exported-fields-app-logs

- request logs: https://github.com/SAP/cf-java-logging-support/blob/master/cf-java-logging-support-core/beats/request-metrics/docs/fields.asciidoc

## [1] What is correlation-id/request id
https://stackoverflow.com/questions/25433258/what-is-the-x-request-id-http-header 
## [2] Python logging propagate
https://docs.python.org/3/library/logging.html#logging.Logger.propagate
https://docs.python.org/2/library/logging.html#logging.Logger.propagate

## [3] more on flask use_reloader
http://flask.pocoo.org/docs/0.12/errorhandling/#working-with-debuggers