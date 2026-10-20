"""Startup patterns for FastAPI applications (issue #106).

The documented working patterns must initialise json-logging exactly once. The pattern from the report, where a
module started as a script also passes an import string to uvicorn, must keep raising the same error.
"""
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "example" / "fastapi_startup"


def _run(code, cwd, extra_path=()):
    env = dict(os.environ, PYTHONWARNINGS="ignore")
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(cwd), *map(str, extra_path)])
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code)], cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=60)


def test_example_app_is_importable_and_initialises_once():
    result = _run("""
        import importlib
        main = importlib.import_module("app.main")
        from uvicorn.importer import import_from_string
        assert import_from_string("app.main:app") is main.app      # what `uvicorn app.main:app` does
        print("OK")
    """, cwd=EXAMPLE)
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_app_object_pattern_initialises_once_without_serving():
    result = _run("""
        from app.main import app
        import json_logging
        assert app is not None and json_logging.get_correlation_id() == json_logging.EMPTY_VALUE
        print("OK")
    """, cwd=EXAMPLE)
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_reported_pattern_still_raises_the_double_initialisation_error(tmp_path):
    """Module run as a script, which also passes an import string to uvicorn, initialises twice."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("")
    (tmp_path / "app" / "main.py").write_text(textwrap.dedent("""
        import fastapi, json_logging
        from uvicorn.importer import import_from_string
        app = fastapi.FastAPI()
        json_logging.init_fastapi(enable_json=True)
        json_logging.init_request_instrument(app)
        if __name__ == "__main__":
            import_from_string("app.main:app")     # imports this module a second time
    """))
    result = _run("import runpy; runpy.run_path('app/main.py', run_name='__main__')", cwd=tmp_path)
    assert result.returncode != 0
    assert "RuntimeError: Can not call init more than once" in result.stderr


def test_second_initialisation_in_one_process_still_raises():
    result = _run("""
        import json_logging
        json_logging.init_fastapi(enable_json=True)
        try:
            json_logging.init_fastapi(enable_json=True)
        except RuntimeError as exc:
            assert "Can not call init more than once" in str(exc)
            print("RAISED")
        else:
            raise AssertionError("Expected duplicate initialization to raise RuntimeError")
    """, cwd=EXAMPLE)
    assert result.returncode == 0, result.stderr
    assert "RAISED" in result.stdout
