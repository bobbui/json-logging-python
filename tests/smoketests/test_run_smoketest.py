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


@pytest.mark.parametrize('backend', collect_backends(), ids=collect_backends())
def test_api_example(backend):
    """For each of the examples start the API and see if the root endpoint is reachable"""
    api_process = subprocess.Popen(
        [sys.executable, Path(__file__).parent / backend / "api.py"],
        stdout=sys.stdout,
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.perf_counter() + 15.0
        while time.perf_counter() < deadline:
            time.sleep(3)
            session = requests.Session()
            session.trust_env = False
            os.environ['NO_PROXY'] = 'localhost'
            os.environ['no_proxy'] = 'localhost'
            try:
                response = requests.get("http://localhost:5000/", timeout=1)
                assert response.status_code == 200
                return
            except requests.exceptions.Timeout:
                pass
        assert False, "API did not respond"
    finally:
        api_process.send_signal(signal.SIGTERM)
        api_process.wait(timeout=5.0)
