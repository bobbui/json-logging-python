"""Test module to run all example APIs and see if they work independently of each other

These tests are meant to be executed independently with only the minimal environment.
This way it becomes clear if json_logging works without the dependencies of API frameworks one
doesn't intend to use.
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests


def collect_backends():
    """Generator function which returns all test backends one by one

    If the environment variable "backend" is set, only this one backend is returned
    """
    preset_backend = os.environ.get('backend')
    if preset_backend:
        yield preset_backend
    else:
        for folder in Path(__file__).parent.iterdir():
            if folder.is_dir() and folder.name != '__pycache__':
                yield str(folder.name)


def wait_for_api(session, url, timeout, poll_interval=3.0):
    """Poll url until it answers or the timeout expires, return whether the API responded

    Connection errors and timeouts are expected while the API is still starting up.
    """
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        time.sleep(poll_interval)
        try:
            response = session.get(url, timeout=1)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            continue
        assert response.status_code == 200
        return True
    return False


def stop_process(process, timeout=5.0):
    """Ask the process to terminate and kill it if it does not exit in time"""
    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@pytest.mark.parametrize('backend', list(collect_backends()))
def test_api_example(backend):
    """For each of the examples start the API and see if the root endpoint is reachable"""
    api_process = subprocess.Popen(
        [sys.executable, str(os.path.join(Path(__file__).parent, backend, "api.py"))],
        stdout=sys.stdout,
        stderr=subprocess.STDOUT,
    )
    try:
        with requests.Session() as session:
            # ignore proxy settings from the environment, the API runs on localhost
            session.trust_env = False
            assert wait_for_api(session, "http://localhost:5000/", timeout=15.0), "API did not respond"
    finally:
        stop_process(api_process)


class _StartingUpSession:
    """Fake session which refuses connections a number of times before answering"""

    def __init__(self, failures):
        self.failures = failures
        self.calls = 0

    def get(self, url, timeout):
        self.calls += 1
        if self.calls <= self.failures:
            raise requests.exceptions.ConnectionError("API not up yet")
        response = requests.Response()
        response.status_code = 200
        return response


def test_wait_for_api_retries_while_api_is_starting():
    session = _StartingUpSession(failures=2)
    assert wait_for_api(session, "http://localhost:5000/", timeout=5.0, poll_interval=0)
    assert session.calls == 3


def test_wait_for_api_gives_up_at_timeout():
    session = _StartingUpSession(failures=float('inf'))
    assert not wait_for_api(session, "http://localhost:5000/", timeout=0.05, poll_interval=0.01)
    assert session.calls > 1


def test_stop_process_kills_process_ignoring_sigterm():
    process = subprocess.Popen(
        [sys.executable, "-c",
         "import signal, sys, time\n"
         "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
         "sys.stdout.write('ready\\n'); sys.stdout.flush()\n"
         "time.sleep(60)"],
        stdout=subprocess.PIPE,
    )
    try:
        process.stdout.readline()  # SIGTERM handler is installed once the child is ready
        stop_process(process, timeout=0.5)
        assert process.poll() is not None
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()
