"""Flask under a real Gunicorn worker (issue #25).

Starts example/gunicorn_flask on a Unix socket, waits until the worker answers HTTP, sends requests, stops the server,
and checks the JSON records written to stdout.

Gunicorn is required in CI (the CI environment variable is set by GitHub Actions): a missing install fails the test
instead of skipping it. Elsewhere the test is skipped when gunicorn or httpx is not installed.
"""
import importlib
import json
import os
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

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "example" / "gunicorn_flask"
STARTUP_TIMEOUT = 30.0      # seconds, monotonic clock
REQUEST_TIMEOUT = 2.0       # seconds per HTTP attempt
STOP_TIMEOUT = 20.0         # seconds for gunicorn to exit after SIGTERM


def _json_records(text):
    """Every line that starts with '{' must be a valid JSON record. Gunicorn's own plain-text lines are skipped."""
    return [json.loads(line) for line in text.splitlines() if line.startswith("{")]


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


def test_gunicorn_worker_logs_application_and_request_with_the_same_correlation_id():
    # A short directory: macOS limits Unix socket paths to about 104 bytes, which pytest's tmp_path can exceed.
    with tempfile.TemporaryDirectory(prefix="gu", dir="/tmp") as tmp:
        _run_gunicorn_check(Path(tmp))


def _run_gunicorn_check(tmp_path):
    socket_path = tmp_path / "gunicorn.sock"
    log_path = tmp_path / "gunicorn.log"
    env = dict(os.environ, PYTHONWARNINGS="ignore", GUNICORN_BIND="unix:" + str(socket_path))
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(EXAMPLE), os.environ.get("PYTHONPATH", "")])
    with open(log_path, "w") as log_file:   # a file rather than a pipe: no deadlock when output is large
        process = subprocess.Popen(
            [sys.executable, "-m", "gunicorn", "-c", str(EXAMPLE / "gunicorn.conf.py"), "--workers", "1", "app:app"],
            cwd=str(EXAMPLE), env=env, stdout=log_file, stderr=subprocess.STDOUT)
    try:
        _wait_until_ready(process, socket_path, log_path)
        with httpx.Client(transport=httpx.HTTPTransport(uds=str(socket_path)), base_url="http://localhost",
                          timeout=REQUEST_TIMEOUT) as client:
            supplied = client.get("/", headers={"X-Correlation-ID": "gunicorn-1"})
            generated = client.get("/")
    finally:
        _stop(process)

    output = log_path.read_text()
    assert supplied.status_code == 200 and generated.status_code == 200
    assert supplied.json() == {"correlation_id": "gunicorn-1"}
    generated_id = generated.json()["correlation_id"]
    assert generated_id not in ("-", "gunicorn-1")

    records = _json_records(output)
    app_ids = [r["correlation_id"] for r in records if r.get("logger") == "app"]
    request_ids = [r["correlation_id"] for r in records if r.get("type") == "request"]
    assert app_ids == ["gunicorn-1", generated_id], output
    assert request_ids == ["gunicorn-1", generated_id], output
    # The /ready probe is excluded from request logging, and accesslog is disabled in gunicorn.conf.py.
    assert not [r for r in records if r.get("logger") == "gunicorn.access"]
