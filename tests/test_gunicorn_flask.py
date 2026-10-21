"""Flask under a real Gunicorn worker (issue #25).

Starts example/gunicorn_flask on a Unix socket, waits until the worker answers HTTP, sends requests, stops the server,
and checks the records written to stdout and stderr.

Gunicorn is required in CI (the CI environment variable is set by GitHub Actions): a missing install fails the test
instead of skipping it. Elsewhere the test is skipped when gunicorn or httpx is not installed.
"""
import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

IN_CI = os.environ.get("CI") == "true"
if IN_CI:
    importlib.import_module("gunicorn")  # fail, do not skip, if the CI install is missing gunicorn
    httpx = importlib.import_module("httpx")
else:
    pytest.importorskip("gunicorn")
    httpx = pytest.importorskip("httpx")

from gunicorn.config import Config as GunicornConfig  # noqa: E402  (after the import guard above)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "example" / "gunicorn_flask"
STARTUP_TIMEOUT = 30.0      # seconds, monotonic clock
REQUEST_TIMEOUT = 2.0       # seconds per HTTP attempt
STOP_TIMEOUT = 20.0         # seconds for gunicorn to exit after SIGTERM
EMPTY_VALUE = "-"           # json_logging.EMPTY_VALUE; json_logging is not imported in this process

# The request line and status of Gunicorn's access log format ('"GET / HTTP/1.1" 200'). Matches the plain-text line
# and the same text inside a JSON record, where the quotes are escaped. json-logging's own request records keep the
# method, path and status in separate fields, so they do not match.
ACCESS_LOG_LINE = re.compile(r'\\?"(?:GET|HEAD|POST|PUT|PATCH|DELETE|OPTIONS) /\S* HTTP/\d(?:\.\d)?\\?" \d{3}\b')


def _json_records(text):
    """Every line that starts with '{' must be a valid JSON record. Gunicorn's own plain-text lines are skipped."""
    return [json.loads(line) for line in text.splitlines() if line.startswith("{")]


def _access_log_lines(text):
    """Gunicorn access-log lines in the raw output, in plain text or JSON form."""
    return [line for line in text.splitlines() if ACCESS_LOG_LINE.search(line)]


def _wait_until_ready(process, socket_path, log_path):
    """Poll the worker over HTTP until /ready answers 200, with a fixed monotonic deadline."""
    deadline = time.monotonic() + STARTUP_TIMEOUT
    last_error = None
    with httpx.Client(transport=httpx.HTTPTransport(uds=str(socket_path)), base_url="http://localhost",
                      timeout=REQUEST_TIMEOUT) as client:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError("gunicorn exited during startup with code %s:\n%s"
                                     % (process.returncode, log_path.read_text()))
            if socket_path.exists():
                try:
                    if client.get("/ready").status_code == 200:
                        return
                except httpx.TransportError as exc:
                    last_error = exc
            time.sleep(0.1)
    raise AssertionError("gunicorn did not answer /ready within %.0fs (last error: %r)\n%s"
                         % (STARTUP_TIMEOUT, last_error, log_path.read_text()))


def _stop(process):
    process.terminate()
    try:
        process.wait(timeout=STOP_TIMEOUT)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _assert_workers_exited(output):
    for pid in re.findall(r"Booting worker with pid: (\d+)", output):
        try:
            os.kill(int(pid), 0)
        except ProcessLookupError:
            continue
        raise AssertionError("gunicorn worker %s is still running after shutdown" % pid)


def _wait_for_ready_workers(process, log_path, count):
    """Wait until `count` workers have logged their startup record. /ready answering only proves that one worker
    is up; with several workers the others may still be importing the app."""
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError("gunicorn exited during startup with code %s:\n%s"
                                 % (process.returncode, log_path.read_text()))
        if len(_worker_ready_records(log_path.read_text())) >= count:
            return
        time.sleep(0.1)
    raise AssertionError("%d gunicorn workers did not start within %.0fs\n%s"
                         % (count, STARTUP_TIMEOUT, log_path.read_text()))


def _worker_ready_records(text):
    # Only complete lines: the log file may be read while a worker is still writing a record.
    lines = [line for line in text.splitlines(keepends=True) if line.endswith("\n")]
    return [r for r in _json_records("".join(lines)) if r.get("logger") == "app" and r.get("msg") == "worker ready"]


def _run_example(extra_args=(), workers=1):
    """Serve the example with `workers` worker processes, send three requests (X-Correlation-ID, X-Request-ID, no
    header), and stop the server.

    Returns (responses keyed "supplied", "request_id" and "generated", raw output). A short directory is used
    because macOS limits Unix socket paths to about 104 bytes, which pytest's tmp_path can exceed.
    """
    with tempfile.TemporaryDirectory(prefix="gu", dir="/tmp") as tmp:
        tmp_path = Path(tmp)
        socket_path = tmp_path / "gunicorn.sock"
        log_path = tmp_path / "gunicorn.log"
        args = ["--workers", str(workers)]
        if "control_socket" in GunicornConfig().settings:   # Gunicorn 25+: keep its control socket out of $HOME
            args += ["--control-socket", str(tmp_path / "gunicorn.ctl")]
        env = dict(os.environ, PYTHONWARNINGS="ignore", GUNICORN_BIND="unix:" + str(socket_path))
        env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(EXAMPLE), os.environ.get("PYTHONPATH", "")])
        with open(log_path, "w") as log_file:   # a file rather than a pipe: no deadlock when output is large
            process = subprocess.Popen(
                [sys.executable, "-m", "gunicorn", "-c", str(EXAMPLE / "gunicorn.conf.py")] + args
                + list(extra_args) + ["app:app"],
                cwd=str(EXAMPLE), env=env, stdout=log_file, stderr=subprocess.STDOUT)
        try:
            _wait_until_ready(process, socket_path, log_path)
            _wait_for_ready_workers(process, log_path, workers)
            with httpx.Client(transport=httpx.HTTPTransport(uds=str(socket_path)), base_url="http://localhost",
                              timeout=REQUEST_TIMEOUT) as client:
                responses = {
                    "supplied": client.get("/", headers={"X-Correlation-ID": "gunicorn-1"}),
                    "request_id": client.get("/", headers={"X-Request-ID": "gunicorn-req-2"}),
                    "generated": client.get("/"),
                }
        finally:
            _stop(process)
        output = log_path.read_text()
    assert process.returncode is not None
    _assert_workers_exited(output)
    return responses, output


def _assert_requests_correlate(responses, records):
    """Each request's response, application log and request record carry the same correlation ID, whichever worker
    handled it. Returns the generated ID."""
    assert all(r.status_code == 200 for r in responses.values())
    ids = {name: r.json()["correlation_id"] for name, r in responses.items()}
    assert ids["supplied"] == "gunicorn-1"
    assert ids["request_id"] == "gunicorn-req-2"
    assert ids["generated"] not in (EMPTY_VALUE, "gunicorn-1", "gunicorn-req-2")
    handled = [r["correlation_id"] for r in records if r.get("logger") == "app" and r.get("msg") == "handled request"]
    request_records = [r for r in records if r.get("type") == "request"]
    assert handled == list(ids.values())
    # Only the "/" requests are logged: the /ready probes are excluded from request instrumentation.
    assert [(r["request"], r["correlation_id"]) for r in request_records] == [("/", i) for i in ids.values()]
    return ids["generated"]


def _assert_worker_lifecycle(output, records, workers):
    """Every booted worker logged its startup record outside a request and a JSON 'Worker exiting' record, both with
    the empty correlation ID."""
    booted = sorted(int(pid) for pid in re.findall(r"Booting worker with pid: (\d+)", output))
    assert len(booted) == workers and len(set(booted)) == workers, output
    ready = [r for r in records if r.get("logger") == "app" and r.get("msg") == "worker ready"]
    assert sorted(r["pid"] for r in ready) == booted, output
    assert {r["correlation_id"] for r in ready} == {EMPTY_VALUE}, output
    exiting = [r for r in records if r.get("logger") == "gunicorn.error" and r["msg"].startswith("Worker exiting")]
    assert sorted(int(re.search(r"pid: (\d+)", r["msg"]).group(1)) for r in exiting) == booted, output
    assert {r["correlation_id"] for r in exiting} == {EMPTY_VALUE}, output


def test_gunicorn_worker_logs_application_and_request_with_the_same_correlation_id():
    responses, output = _run_example()
    records = _json_records(output)

    _assert_requests_correlate(responses, records)
    _assert_worker_lifecycle(output, records, workers=1)
    # accesslog = None in gunicorn.conf.py: no Gunicorn access line, in plain text or JSON, for any request.
    assert _access_log_lines(output) == [], output
    assert not [r for r in records if r.get("logger") == "gunicorn.access"], output


def test_two_workers_start_log_and_exit_cleanly():
    """The example's configured worker count. Which worker serves a request is up to Gunicorn, so request checks are
    per request; the lifecycle checks are per worker."""
    responses, output = _run_example(workers=2)
    records = _json_records(output)

    _assert_worker_lifecycle(output, records, workers=2)
    _assert_requests_correlate(responses, records)
    assert _access_log_lines(output) == [], output


def test_access_log_detector_finds_lines_when_gunicorn_access_logging_is_enabled():
    """Negative control: with Gunicorn's access log turned on, the detector above must report the extra lines."""
    responses, output = _run_example(["--access-logfile", "-"])

    assert all(r.status_code == 200 for r in responses.values())
    access_lines = _access_log_lines(output)
    assert len([line for line in access_lines if "GET / HTTP/1.1" in line]) == 3, output
    assert [line for line in access_lines if "GET /ready HTTP/1.1" in line], output    # Gunicorn logs probes too
    # json-logging still writes its own request records, so each "/" request now has two access records.
    assert len([r for r in _json_records(output) if r.get("type") == "request"]) == 3, output
