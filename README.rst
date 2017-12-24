json-logging
============

Python logging library to emit JSON log that can be easily indexed and
searchable by logging infrastructure such as
`ELK <https://www.elastic.co/webinars/introduction-elk-stack>`_.

| If you’re using Cloud Foundry, it worth to check out the library
  `SAP/cf-python-logging-support <https://github.com/SAP/cf-python-logging-support>`_
  which I’m also original author and contributor. 

1. Features
===========

1. Emit JSON logs (see format
   detail in reference)
2. Support **correlation-id**
   `[1] <https://stackoverflow.com/questions/25433258/what-is-the-x-request-id-http-header>`_
3. Lightweight, no dependencies, minimal configuration needed (1 LoC to
   get it working)
4. Fully compatible with Python **logging** module. Support both Python
   2.7.x and 3.x
5. Support HTTP request instrumentation. Built in support for
   `Flask <http://flask.pocoo.org/>`_ &
   `Sanic <https://github.com/channelcat/sanic>`_. Extensible to support other web
   frameworks. PR welcome :smiley: .
6. Support inject arbitrary extra properties to JSON log message.

2. Usage
========

Install by running this command: 

.. code:: python

    pip install json-logging

By default log will be emitted in normal format to ease the local
development. To enable it on production set either
**json_logging.ENABLE_JSON_LOGGING** or **ENABLE_JSON_LOGGING
environment variable** to true.

| To configure, call **json_logging.init(framework_name)**. Once
  configured library will try to configure all loggers (existing and
  newly created) to emit log in JSON format.
| See following use cases for more detail.

| TODO: update guide on how to use ELK stack to view log


2.1 Non-web application log
---------------------------

This mode don’t support **correlation-id**.

.. code:: python

    import json_logging, logging, sys

    # log is initialized without a web framework name
    json_logging.ENABLE_JSON_LOGGING = True
    json_logging.init()

    logger = logging.getLogger("test-logger")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(sys.stdout))

    logger.info("test logging statement")


2.2 Web application log
-----------------------


Flask
~~~~~

.. code:: python

    import datetime, logging, sys, json_logging, flask

    app = flask.Flask(__name__)
    json_logging.ENABLE_JSON_LOGGING = True
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


Sanic
~~~~~

.. code:: python

    import logging, sys, json_logging, sanic

    app = sanic.Sanic()
    json_logging.ENABLE_JSON_LOGGING = True
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


2.3 Get current correlation-id
------------------------------

Current request correlation-id can be retrieved and pass to downstream
services call as follow:

.. code:: python

    correlation_id = json_logging.get_correlation_id()
    # use correlation id for downstream service calls here

In request context, if one is not present, a new one might be generated
depends on CREATE_CORRELATION_ID_IF_NOT_EXISTS setting value.


2.4 Log extra properties
------------------------

Extra property can be added to logging statement as follow:

.. code:: python

    logger.info("test log statement", extra = {'props' : {'extra_property' : 'extra_value'}})


2.5 Root logger
---------------

If you want to use root logger as main logger to emit log. Made sure you
call **config_root_logger()** after initialize root logger (by
logging.basicConfig() or logging.getLogger(‘root’))
`[2] <#2-python-logging-propagate>`_

.. code:: python

    logging.basicConfig()
    json_logging.config_root_logger()


3. Configuration
================

logging library can be configured by setting the value in json_logging

+-------------------------------------+----------------------+----------------------+
| Name                                | Description          | Default value        |
+=====================================+======================+======================+
| ENABLE_JSON_LOGGING                 | Whether to enable    | false                |
|                                     | JSON logging         |                      |
|                                     | mode.Can be set as   |                      |
|                                     | an environment       |                      |
|                                     | variable, enable     |                      |
|                                     | when set to to       |                      |
|                                     | either one in        |                      |
|                                     | following list       |                      |
|                                     | (case-insensitive)   |                      |
|                                     | **[‘true’, ‘1’, ‘y’, |                      |
|                                     | ‘yes’]**             |                      |
+-------------------------------------+----------------------+----------------------+
| ENABLE_JSON_LOGGING_DEBUG           | Whether to enable    | true                 |
|                                     | debug logging for    |                      |
|                                     | this library for     |                      |
|                                     | development purpose. |                      |
+-------------------------------------+----------------------+----------------------+
| CORRELATION_ID_HEADERS              | List of HTTP headers | [‘X-Correlation-ID’, |
|                                     | that will be used to | ‘X-Request-ID’]      |
|                                     | look for             |                      |
|                                     | correlation-id       |                      |
|                                     | value. HTTP headers  |                      |
|                                     | will be searched one |                      |
|                                     | by one according to  |                      |
|                                     | list order           |                      |
+-------------------------------------+----------------------+----------------------+
| EMPTY_VALUE                         | Default value when a | ‘-’                  |
|                                     | logging record       |                      |
|                                     | property is None     |                      |
+-------------------------------------+----------------------+----------------------+
| CORRELATION_ID_GENERATOR            | function to generate | uuid.uuid1           |
|                                     | unique               |                      |
|                                     | correlation-id       |                      |
+-------------------------------------+----------------------+----------------------+
| JSON_SERIALIZER                     | function to encode   | json.dumps           |
|                                     | object to JSON       |                      |
+-------------------------------------+----------------------+----------------------+
| COMPONENT_ID                        | Uniquely identifies  | EMPTY_VALUE          |
|                                     | the software         |                      |
|                                     | component that has   |                      |
|                                     | processed the        |                      |
|                                     | current request      |                      |
+-------------------------------------+----------------------+----------------------+
| COMPONENT_NAME                      | A human-friendly     | EMPTY_VALUE          |
|                                     | name representing    |                      |
|                                     | the software         |                      |
|                                     | component            |                      |
+-------------------------------------+----------------------+----------------------+
| COMPONENT_INSTANCE_INDEX            | Instance’s index of  | 0                    |
|                                     | horizontally scaled  |                      |
|                                     | service              |                      |
+-------------------------------------+----------------------+----------------------+
| CREATE_CORRELATION_ID_IF_NOT_EXISTS | Whether to generate  | True                 |
|                                     | a new correlation-id |                      |
|                                     | in case one is not   |                      |
|                                     | present              |                      |
+-------------------------------------+----------------------+----------------------+


4. Python References
====================

TODO: update Python API docs on Github page


5. Framework support plugin development
=======================================

To add support for a new web framework, you need to extend following
classes in
`**framework_base** <https://github.com/thangbn/json-logging-python/blob/master/json_logging/framework_base.py>`_ and
register support using
`**json_logging.register_framework_support** <https://github.com/thangbn/json-logging-python/blob/master/json_logging/__init__.py#L38>`_
method:

+---------------------------------------+----------------------+----------------------+
| Class                                 | Description          | Mandatory            |
+=======================================+======================+======================+
| RequestAdapter                        | Helper class help to | no                   |
|                                       | extract              |                      |
|                                       | logging-relevant     |                      |
|                                       | information from     |                      |
|                                       | HTTP request object  |                      |
+---------------------------------------+----------------------+----------------------+
| ResponseAdapter                       | Helper class help to | yes                  |
|                                       | extract              |                      |
|                                       | logging-relevant     |                      |
|                                       | information from     |                      |
|                                       | HTTP response object |                      |
+---------------------------------------+----------------------+----------------------+
| FrameworkConfigurator                 | Class to perform     | no                   |
|                                       | logging              |                      |
|                                       | configuration for    |                      |
|                                       | given framework as   |                      |
|                                       | needed               |                      |
+---------------------------------------+----------------------+----------------------+
| AppRequestInstrumentationConfigurator | Class to perform     | no                   |
|                                       | request              |                      |
|                                       | instrumentation      |                      |
|                                       | logging              |                      |
|                                       | configuration        |                      |
+---------------------------------------+----------------------+----------------------+

Take a look at
`**json_logging/base_framework.py** <https://github.com/thangbn/json-logging-python/blob/master/json_logging/framework_base.py>`_,
`**json_logging.flask** <https://github.com/thangbn/json-logging-python/tree/master/json_logging/framework/flask>`_
and
`**json_logging.sanic** <https://github.com/thangbn/json-logging-python/tree/master/json_logging/framework/sanic>`_
packages for reference implementations.


6. FAQ & Troubleshooting
========================

1. I configured everything, but no logs are printed out?

   -  Forgot to add handlers to your logger?
   -  Check whether logger is disabled.

2. Same log statement is printed out multiple times.

   -  Check whether the same handler is added to both parent and child
      loggers [2]
   -  If you using flask, by default option **use_reloader** is set to
      **True** which will start 2 instances of web application. change
      it to False to disable this behaviour
      `[3] <#3-more-on-flask-use-reloader>`_

3. Can not install Sanic on Windows?

you can install Sanic on windows by running these commands:

::

    git clone --branch 0.7.0 https://github.com/channelcat/sanic.git
    set SANIC_NO_UVLOOP=true
    set SANIC_NO_UJSON=true
    pip3 install .


7. References
=============

[0] Full logging format references
----------------------------------

2 types of logging statement will be emitted by this library: 
- Application log: normal logging statement e.g.:

::

    {
        "type": "log",
        "written_at": "2017-12-23T16:55:37.280Z",
        "written_ts": 1514048137280721000,
        "component_id": "1d930c0xd-19-s3213",
        "component_name": "ny-component_name",
        "component_instance": 0,
        "logger": "test logger",
        "thread": "MainThread",
        "level": "INFO",
        "line_no": 22,
        "correlation_id": "1975a02e-e802-11e7-8971-28b2bd90b19a",
        "extra_property": "extra_value"
    }

-  Request log: request instrumentation logging statement which recorded
   request information such as response time, request size, etc.

::

    {
        "type": "request",
        "written_at": "2017-12-23T16:55:37.280Z",
        "written_ts": 1514048137280721000,
        "component_id": "-",
        "component_name": "-",
        "component_instance": 0,
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

See following tables for detail format explanation: 

 - Common field

+-------------------+-----------------+-----------------+-----------------+
| Field             | Description     | Format          | Example         |
+===================+=================+=================+=================+
| written_at        | The date when   | ISO 8601        | 2017-12-23T15:1 |
|                   | this log        | YYYY-MM-DDTHH:M | 4:02.208Z       |
|                   | message was     | M:SS.milliZ     |                 |
|                   | written.        |                 |                 |
+-------------------+-----------------+-----------------+-----------------+
| written_ts        | The timestamp   | long number     | 145682055381684 |
|                   | in nano-second  |                 | 9408            |
|                   | precision when  |                 |                 |
|                   | this request    |                 |                 |
|                   | metric message  |                 |                 |
|                   | was written.    |                 |                 |
+-------------------+-----------------+-----------------+-----------------+
| correlation_id    | The timestamp   | string          | db2d002e-2702-4 |
|                   | in nano-second  |                 | 1ec-66f5-c002a8 |
|                   | precision when  |                 | 0a3d3f          |
|                   | this request    |                 |                 |
|                   | metric message  |                 |                 |
|                   | was written.    |                 |                 |
+-------------------+-----------------+-----------------+-----------------+
| type              | Type of         | string          |                 |
|                   | logging. “logs” |                 |                 |
|                   | or “request”    |                 |                 |
+-------------------+-----------------+-----------------+-----------------+
| component_id      | Uniquely        | string          | 9e6f3ecf-def0-4 |
|                   | identifies the  |                 | baf-8fac-9339e6 |
|                   | software        |                 | 1d5645          |
|                   | component that  |                 |                 |
|                   | has processed   |                 |                 |
|                   | the current     |                 |                 |
|                   | request         |                 |                 |
+-------------------+-----------------+-----------------+-----------------+
| component_name    | A               | string          | my-component    |
|                   | human-friendly  |                 |                 |
|                   | name            |                 |                 |
|                   | representing    |                 |                 |
|                   | the software    |                 |                 |
|                   | component       |                 |                 |
+-------------------+-----------------+-----------------+-----------------+
| component_instance| Instance’s      | string          | 0               |
|                   | index of        |                 |                 |
|                   | horizontally    |                 |                 |
|                   | scaled service  |                 |                 |
+-------------------+-----------------+-----------------+-----------------+

 -  application logs

+-----------------+-----------------+-----------------+-----------------+
| Field           | Description     | Format          | Example         |
+=================+=================+=================+=================+
| msg             | The actual      | string          | This is a log   |
|                 | message string  |                 | message         |
|                 | passed to the   |                 |                 |
|                 | logger.         |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| level           | The log “level” | string          | INFO            |
|                 | indicating the  |                 |                 |
|                 | severity of the |                 |                 |
|                 | log message.    |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| thread          | Identifies the  | string          | http-nio-4655   |
|                 | execution       |                 |                 |
|                 | thread in which |                 |                 |
|                 | this log        |                 |                 |
|                 | message has     |                 |                 |
|                 | been written.   |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| logger          | The logger name |                 |                 |
|                 | that emits the  |  string         |requests-logger  |
|                 | log message.    |                 |                 |
+-----------------+-----------------+-----------------+-----------------+

 -  request logs:

+-----------------+-----------------+-----------------+-----------------+
| Field           | Description     | Format          | Example         |
+=================+=================+=================+=================+
| request         | request path    | string          | /get/api/v2     |
|                 | that has been   |                 |                 |
|                 | processed.      |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| request_receive | The date when   | ISO 8601        | 2015-01-24      |
| d_at            | an incoming     | YYYY-MM-DDTHH:M | 14:06:05.071Z   |
|                 | request was     | M:SS.milliZ     |                 |
|                 | received by the | The precision   |                 |
|                 | producer.       | is in           |                 |
|                 |                 | milliseconds.   |                 |
|                 |                 | The timezone is |                 |
|                 |                 | UTC.            |                 |
+-----------------+-----------------+-----------------+-----------------+
| response_sent_a | The date when   | ditto           | 2015-01-24      |
| t               | the response to |                 | 14:06:05.071Z   |
|                 | an incoming     |                 |                 |
|                 | request was     |                 |                 |
|                 | sent to the     |                 |                 |
|                 | consumer.       |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| response_time_m | How many        | float           | 43.476          |
| s               | milliseconds it |                 |                 |
|                 | took the        |                 |                 |
|                 | producer to     |                 |                 |
|                 | prepare the     |                 |                 |
|                 | response.       |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| protocol        | Which protocol  | string          | HTTP/1.1        |
|                 | was used to     |                 |                 |
|                 | issue a request |                 |                 |
|                 | to a producer.  |                 |                 |
|                 | In most cases,  |                 |                 |
|                 | this will be    |                 |                 |
|                 | HTTP (including |                 |                 |
|                 | a version       |                 |                 |
|                 | specifier), but |                 |                 |
|                 | for outgoing    |                 |                 |
|                 | requests        |                 |                 |
|                 | reported by a   |                 |                 |
|                 | producer, it    |                 |                 |
|                 | may contain     |                 |                 |
|                 | other values.   |                 |                 |
|                 | E.g. a database |                 |                 |
|                 | call via JDBC   |                 |                 |
|                 | may report,     |                 |                 |
|                 | e.g. “JDBC/1.2” |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| method          | The             | string          | GET             |
|                 | corresponding   |                 |                 |
|                 | protocol        |                 |                 |
|                 | method.         |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| remote_ip       | IP address of   | string          | 192.168.0.1     |
|                 | the consumer    |                 |                 |
|                 | (might be a     |                 |                 |
|                 | proxy, might be |                 |                 |
|                 | the actual      |                 |                 |
|                 | client)         |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| remote_host     | host name of    | string          | my.happy.host   |
|                 | the consumer    |                 |                 |
|                 | (might be a     |                 |                 |
|                 | proxy, might be |                 |                 |
|                 | the actual      |                 |                 |
|                 | client)         |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| remote_port     | Which TCP port  | string          | 1234            |
|                 | is used by the  |                 |                 |
|                 | consumer to     |                 |                 |
|                 | establish a     |                 |                 |
|                 | connection to   |                 |                 |
|                 | the remote      |                 |                 |
|                 | producer.       |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| remote_user     | The username    | string          | user_name       |
|                 | associated with |                 |                 |
|                 | the request     |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| request_size_b  | The size in     | long            | 1234            |
|                 | bytes of the    |                 |                 |
|                 | requesting      |                 |                 |
|                 | entity or       |                 |                 |
|                 | “body” (e.g.,   |                 |                 |
|                 | in case of POST |                 |                 |
|                 | requests).      |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| response_size_b | The size in     | long            | 1234            |
|                 | bytes of the    |                 |                 |
|                 | response entity |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| response_status | The status code | long            | 200             |
|                 | of the          |                 |                 |
|                 | response.       |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| response_conten | The MIME type   | long            | application/jso |
| t_type          | associated with |                 | n               |
|                 | the entity of   |                 |                 |
|                 | the response if |                 |                 |
|                 | available or    |                 |                 |
|                 | specified       |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| referer         | For HTTP        | string          | /index.html     |
|                 | requests,       |                 |                 |
|                 | identifies the  |                 |                 |
|                 | address of the  |                 |                 |
|                 | webpage         |                 |                 |
|                 | (i.e. the URI   |                 |                 |
|                 | or IRI) that    |                 |                 |
|                 | linked to the   |                 |                 |
|                 | resource being  |                 |                 |
|                 | requested.      |                 |                 |
+-----------------+-----------------+-----------------+-----------------+
| x_forwarded_for | Comma-separated | string          | 192.0.2.60,10.1 |
|                 | list of IP      |                 | 2.9.23          |
|                 | addresses, the  |                 |                 |
|                 | left-most being |                 |                 |
|                 | the original    |                 |                 |
|                 | client,         |                 |                 |
|                 | followed by     |                 |                 |
|                 | proxy server    |                 |                 |
|                 | addresses that  |                 |                 |
|                 | forwarded the   |                 |                 |
|                 | client request. |                 |                 |
+-----------------+-----------------+-----------------+-----------------+

[1] What is correlation-id/request id
-------------------------------------

https://stackoverflow.com/questions/25433258/what-is-the-x-request-id-http-header

[2] Python logging propagate
----------------------------
https://docs.python.org/3/library/logging.html#logging.Logger.propagate
https://docs.python.org/2/library/logging.html#logging.Logger.propagate

[3] more on flask use_reloader
------------------------------

http://flask.pocoo.org/docs/0.12/errorhandling/#working-with-debuggers