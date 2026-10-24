"""get_request_logger() error handling before request instrumentation is configured."""
import pytest
from helpers.imports import undo_imports_from_package


@pytest.fixture
def fresh_json_logging():
    undo_imports_from_package("json_logging")
    import json_logging
    yield json_logging
    undo_imports_from_package("json_logging")


def test_get_request_logger_after_init_but_before_request_instrumentation_raises_runtime_error(fresh_json_logging):
    fresh_json_logging.init_flask()
    with pytest.raises(RuntimeError, match="init request instrument first"):
        fresh_json_logging.get_request_logger()
