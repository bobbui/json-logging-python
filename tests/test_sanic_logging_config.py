"""Regression tests for Sanic default logging formatter compatibility.

Sanic 24+ removes the legacy 'format' keys from generic/access formatters.
Run each initialization in a fresh Python process because json_logging.init_sanic()
changes process-global state and intentionally cannot be called twice.
"""
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("config_shape", ["legacy", "modern", "installed"])
def test_init_sanic_handles_logging_formats_and_emits_json(config_shape):
    """Both old and new Sanic config shapes initialize and produce parseable JSON records."""
    code = textwrap.dedent("""
        import io
        import json
        import logging
        import sanic.log
        import json_logging

        config_shape = %(config_shape)r
        if config_shape != "installed":
            formatters = {
                "generic": {"format": "%%(message)s"} if config_shape == "legacy" else {},
                "access": {"format": "%%(message)s"} if config_shape == "legacy" else {},
            }
            sanic.log.LOGGING_CONFIG_DEFAULTS = {
                "disable_existing_loggers": True,
                "formatters": formatters,
            }

        json_logging.init_sanic(enable_json=True)
        defaults = sanic.log.LOGGING_CONFIG_DEFAULTS
        assert defaults["disable_existing_loggers"] is False
        logger = logging.getLogger("sanic-formatter-test")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        for name in ("generic", "access"):
            formatter_config = defaults["formatters"][name]
            assert formatter_config["class"] == "json_logging.JSONLogFormatter"
            assert "format" not in formatter_config

            output = io.StringIO()
            handler = logging.StreamHandler(output)
            formatter_class = getattr(json_logging, formatter_config["class"].rsplit(".", 1)[-1])
            handler.setFormatter(formatter_class())
            logger.addHandler(handler)
            try:
                logger.info("sanic json logging", extra={"service": name})
            finally:
                logger.removeHandler(handler)
                handler.close()
            record = json.loads(output.getvalue().strip())
            assert record["type"] == "log"
            assert record["msg"] == "sanic json logging"
            assert record["service"] == name
        print("PASS")
    """ % {"config_shape": config_shape})
    env = dict(os.environ, PYTHONWARNINGS="ignore")
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=str(ROOT), env=env,
        capture_output=True, text=True, timeout=40,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
