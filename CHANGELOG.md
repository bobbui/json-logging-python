# Change Log

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](http://semver.org/).  
The format is based on [Keep a Changelog](http://keepachangelog.com/).
## Unreleased

### Added

- `init_request_instrument(..., read_request_body=True)` (FastAPI only) reads the body of each logged request before the
  handler runs and exposes it as `request.state.json_logging_request_body` (bytes), so a custom request formatter can use
  it without `await` (#84). It is off by default and the body is never added to the log automatically. The whole body is
  held in memory. The handler can still read the body. It needs Starlette 0.28 or newer and raises `RuntimeError` otherwise. Other frameworks raise `ValueError` if it is requested.

### Fixed

- `get_request_logger()` now raises the documented `RuntimeError` instead of `AttributeError` when called before `init_request_instrument()`.

## 1.6.0 - 2026-10-21

### Added

- `json_logging.EXCLUDED_FIELDS`: an optional list, tuple, set or frozenset of field names to omit from every JSON
  record (application, web and request logs, including `extra` and `props` entries). The default is `()`, so
  existing applications need no change and their output fields stay the same. Set it before `init_*()`; formatters
  read it when they are created. An invalid value (a bare string, or a non-string entry) raises `TypeError` from
  `init_*()` or `init_request_instrument()` before any state changes, so it can be corrected and retried. This is
  an output-formatting option, not a security redaction control. (#129, fixes #98)

### Fixed

- FastAPI: application logs and `json_logging.get_correlation_id()` use the request's correlation ID instead of `-`
  in synchronous (`def`) endpoints. When request instrumentation is enabled with `init_request_instrument(app)`, the
  current request is kept in a context variable for the duration of the request, including for URLs excluded from
  request logging. It is visible to `def` and `async def` endpoints, sync and async `BackgroundTasks`,
  `StreamingResponse` iterators, and work that inherits the request's context, such as `asyncio.create_task()`
  (also after the response is sent), `asyncio.to_thread()`, `contextvars.copy_context().run()` and AnyIO/Starlette
  threadpool workers. Without a correlation header, one ID is created at the start of each request, so all logs of
  that request share it. (#123, fixes #124)
- Flask, Quart and Connexion: log records emitted outside an active HTTP request get `-`, as documented, instead of a
  new random correlation ID per record. Connexion 3 error handlers and ASGI middleware, which run outside the Flask
  request context, still use the request's correlation header; without one they get `-`, because a generated ID is
  only stored inside the Flask request context. (#127, fixes #125)
- `json_logging.get_correlation_id()` returns `-` after `init_non_web()`, or before any `init_*()`, instead of
  raising `AttributeError`. (#128, fixes #126)
- Sanic: `init_sanic()` no longer raises `KeyError: 'format'` with Sanic 24.x and later, whose default logging
  configuration omits formatter `format` keys. Older Sanic configurations are still supported. (#133)

### Documentation

- FastAPI and Uvicorn startup: why `RuntimeError: Can not call init more than once` occurs when a module started as a
  script also passes an import string to uvicorn, two working startup patterns, reload and multiple workers, and a
  tested example in `example/fastapi_startup`. The duplicate-initialisation guard is unchanged. (#130, fixes #106)
- Gunicorn and Flask: a tested example in `example/gunicorn_flask` covering initialisation once per worker, request
  instrumentation, correlation IDs, which output is JSON and on which stream, and Gunicorn's access and error logs;
  with integration tests that run real Gunicorn workers. (#131, fixes #25)

### Compatibility

- No change is required from existing applications. With `EXCLUDED_FIELDS` left at its default, the JSON fields of
  every record are the same as in 1.5.1; fields are only removed when an application lists them.
- Behaviour changes in several framework integrations, as listed under Fixed: outside-request records now get `-`
  instead of a random ID (Flask, Quart, Connexion), non-web `get_correlation_id()` no longer raises, FastAPI
  synchronous endpoints now get the request's ID, and Sanic 24+ initialises.
- The FastAPI request-context propagation is used on Python 3.9 and later. Python 3.8 and earlier keep the previous
  behaviour: call-stack lookup only, and no correlation ID created at the start of the request.
- In FastAPI, threads that do not inherit the request's context (`threading.Thread`, `loop.run_in_executor()`),
  WebSocket endpoints, and applications without `init_request_instrument(app)` keep the previous behaviour. There, a
  thread or handler finds the request only if the request object is in one of its own frames, for example as a
  `request` argument; otherwise it logs `-`.
- CI runs the unit tests on Python 3.9 to 3.14 and the Flask, Quart, FastAPI and Sanic smoke tests on Python 3.9 and
  3.14. Python 3.8 and earlier, including Python 2, are not tested.

## 1.5.1 - 2025-07-06

- fix: wrap debug log when logger upated to using JSONLogFormatter #105
- fix: add connexion 3 support #108
- fix: update utcnow for python 3.12 deprecation #107

## 1.5.0-rc0 - 2022-02-01 

- refactoring to have cleaner structure and smaller module

## 1.4.1rc0 - 2021-04-23

- fix #77 Implement extra properties from json-logging-py

## 1.4.0rc2 - 2021-04-23

- allow overriding of correlation id

## 1.4.0rc1 - 2021-04-09

- refactor

## 1.4.0rc - 2021-04-09

- add capability to customize extraction of request, response info #68

## 1.3.0 - 2021-03-25

- add fastapi support #65

## 1.2.11 - 2020-11-07

- fix Sanip IP information is a str not a list #63

## 1.2.10 - 2020-10-15

- re fix #61 Using root logger + flask outside of flask request context throws RuntimeError

## 1.2.9 - 2020-10-15

- Fix #61 Using root logger + flask outside of flask request context throws RuntimeError

## 1.2.8 - 2020-08-27

- Fix #57

## 1.2.7 - 2020-08-27

- yanked, wrong branch released

## 1.2.6 - 2020-08-05

- Fix condition for checking root logger handlers #53

## 1.2.5 - 2020-08-04

- fix #44

## 1.2.4 - 2020-08-03

- fix #51

## 1.2.2 - 2020-07-14

- fix #50

## 1.2.1 - 2020-07-14

- fix #49

## 1.2.0 - 2020-04-10

- fix #45
- fix #46
- refactoring
- optimization log record

## 1.1.0 - 2020-04-10

- Add the possibility to modify the formatter for request logs.

## 1.0.4 - 2019-07-20

- fix #30

## 1.0.3 - 2019-07-20

- add missing kwargs for init_non_web

## 1.0.2 - 2019-07-20

- add method to support getting request logger by using method json_logging.get_request_logger(), fix #23

## 1.0.1 - 2019-07-20

- prevent log forging, fix #1

## 1.0.0 - 2019-07-20

Breaking change:

- add more specific init method for each framework
- minor correct for ENABLE_JSON_LOGGING_DEBUG behaviour
- update few code comments

## 0.1.2 - 2019-06-25

- fix: add japanese character encoding for json logger #24

## 0.1.1 - 2019-05-22

- fix: connexion under gunicorn has no has_request() #22

## 0.1.0 - 2019-05-20

- Add [Connexion](https://github.com/zalando/connexion) support

## 0.0.13 - 2019-05-18

- Fix #19

## 0.0.12 - 2019-02-26

- Fix #16

## 0.0.11 - 2019-01-26

- Adds functionality to customize the the JSON - change keys, values, etc.

## 0.0.10 - 2018-12-04

- Support for exception tracing exception

## 0.0.9 - 2018-10-16

- Add Quart framework support

## 0.0.2 - 2017-12-24

### Changed

- fixed https://github.com/thangbn/json-logging-python/pull/2

## 0.0.1 - 2017-12-24

### Changed

- Initial release
