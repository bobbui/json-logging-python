"""Flask under a real Gunicorn worker (issue #25).

Starts example/gunicorn_flask on a Unix socket, sends requests, stops the server, and checks the JSON records written to
stdout. Skipped when gunicorn or httpx is not installed.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("gunicorn")
httpx = pytest.importorskip("httpx")

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "example" / "gunicorn_flask"


def _json_records(text):
    records = []
    for line in text.splitlines():
        try:
            records.append(json.loads(line))
        except ValueError:
            pass  # gunicorn's own plain-text lines, such as "Starting gunicorn"
    return records


def test_gunicorn_worker_logs_application_and_request_with_the_same_correlation_id(tmp_path):
    socket_path = tmp_path / "gunicorn.sock"
    env = dict(os.environ, PYTHONWARNINGS="ignore", GUNICORN_BIND="unix:" + str(socket_path))
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(EXAMPLE), os.environ.get("PYTHONPATH", "")])
    process = subprocess.Popen(
        [sys.executable, "-m", "gunicorn", "-c", str(EXAMPLE / "gunicorn.conf.py"), "--workers", "1", "app:app"],
        cwd=str(EXAMPLE), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        deadline = time.time() + 30
        while not socket_path.exists() and time.time() < deadline and process.poll() is None:
            time.sleep(0.1)
        assert socket_path.exists(), "gunicorn did not start listening"

        with httpx.Client(transport=httpx.HTTPTransport(uds=str(socket_path)), base_url="http://localhost") as client:
            supplied = client.get("/", headers={"X-Correlation-ID": "gunicorn-1"})
            generated = client.get("/")
    finally:
        process.terminate()
        try:
            output, _ = process.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate()

    assert supplied.status_code == 200 and generated.status_code == 200
    assert supplied.json() == {"correlation_id": "gunicorn-1"}
    generated_id = generated.json()["correlation_id"]
    assert generated_id not in ("-", "gunicorn-1")

    records = _json_records(output)
    app_ids = [r["correlation_id"] for r in records if r.get("logger") == "app"]
    request_ids = [r["correlation_id"] for r in records if r.get("type") == "request"]
    assert app_ids == ["gunicorn-1", generated_id]
    assert request_ids == ["gunicorn-1", generated_id]
    # accesslog is disabled in gunicorn.conf.py, so there is no second, Gunicorn-formatted access line.
    assert not [r for r in records if r.get("logger") == "gunicorn.access"]
