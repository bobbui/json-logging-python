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


def test_import_string_pattern_loads_the_app_through_uvicorn_config_and_initialises_once():
    """`python -m uvicorn app.main:app` builds a uvicorn.Config from the import string and calls load(), which
    imports app.main. Run that real Config.load() path, without starting a server, and check that the loaded
    application is app.main.app and that init_fastapi() ran once."""
    result = _run("""
        import socket, sys
        import json_logging, uvicorn

        init_calls = []
        real_init_fastapi = json_logging.init_fastapi
        def counting_init_fastapi(*args, **kwargs):
            init_calls.append(1)
            return real_init_fastapi(*args, **kwargs)
        json_logging.init_fastapi = counting_init_fastapi

        def no_bind(self, address):
            raise AssertionError("Config.load() must not bind a socket: %r" % (address,))
        socket.socket.bind = no_bind

        config = uvicorn.Config("app.main:app")
        config.load()

        app = config.loaded_app
        while app is not sys.modules["app.main"].app and hasattr(app, "app"):
            app = app.app       # uvicorn wraps the application in its own ASGI middleware
        assert app is sys.modules["app.main"].app, "uvicorn did not load app.main:app"
        assert len(init_calls) == 1, "init_fastapi() ran %d times" % len(init_calls)
        print("OK")
    """, cwd=EXAMPLE)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout


LAUNCHER_CHECK = """
    import runpy, sys
    import json_logging, uvicorn

    init_calls = []
    real_init_fastapi = json_logging.init_fastapi
    def counting_init_fastapi(*args, **kwargs):
        init_calls.append(1)
        return real_init_fastapi(*args, **kwargs)
    json_logging.init_fastapi = counting_init_fastapi

    run_calls = []
    uvicorn.run = lambda app, *args, **kwargs: run_calls.append(app)    # record instead of serving

    runpy.run_path(%(launcher)r, run_name="__main__")

    assert len(run_calls) == 1, run_calls
    assert not isinstance(run_calls[0], str), "uvicorn.run() got an import string: %%r" %% (run_calls[0],)
    assert run_calls[0] is sys.modules["app.main"].app, "uvicorn.run() did not get the app object from app.main"
    assert len(init_calls) == 1, "init_fastapi() ran %%d times" %% len(init_calls)
    print("OK")
"""


def test_app_object_launcher_passes_the_app_to_uvicorn_and_initialises_once():
    """Runs example/fastapi_startup/run.py as `python run.py` would, with uvicorn.run() replaced by a recorder."""
    result = _run(LAUNCHER_CHECK % {"launcher": "run.py"}, cwd=EXAMPLE)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK" in result.stdout


@pytest.mark.parametrize("launch", [
    'import importlib, app.main\nimportlib.reload(app.main)\nuvicorn.run(app.main.app)',   # initialises again
    'uvicorn.run("app.main:app")',                                                         # import string
])
def test_launcher_check_detects_a_launcher_that_reimports_the_app(tmp_path, launch):
    """Negative control: the check above must fail for launchers that do not follow the documented pattern."""
    launcher = tmp_path / "bad_run.py"
    launcher.write_text("import uvicorn\nfrom app.main import app\nif __name__ == '__main__':\n"
                        + textwrap.indent(launch, "    ") + "\n")
    result = _run(LAUNCHER_CHECK % {"launcher": str(launcher)}, cwd=EXAMPLE)
    assert result.returncode != 0
    assert "OK" not in result.stdout


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
