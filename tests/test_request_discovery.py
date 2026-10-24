"""Call-stack request discovery and cached exception text (issue #137)."""
import logging

import pytest
from helpers.imports import undo_imports_from_package


class FakeRequest:
    """Stand-in for a framework request class."""


@pytest.fixture
def request_util():
    from json_logging import util
    from json_logging.framework_base import BaseRequestInfoExtractor, BaseResponseInfoExtractor

    class FakeRequestInfoExtractor(BaseRequestInfoExtractor):
        @staticmethod
        def get_request_class_type():
            return FakeRequest

        @staticmethod
        def support_global_request_object():
            return False

    yield util.RequestUtil(
        request_info_extractor_class=FakeRequestInfoExtractor,
        response_info_extractor_class=BaseResponseInfoExtractor,
    )
    undo_imports_from_package("json_logging")


def test_request_is_found_in_a_local_named_request(request_util):
    request = FakeRequest()

    assert request_util.get_request_from_call_stack() is request


def test_request_is_found_in_a_local_named_req(request_util):
    req = FakeRequest()

    assert request_util.get_request_from_call_stack() is req


def test_request_is_found_in_a_local_with_any_name(request_util):
    something_else = FakeRequest()

    assert request_util.get_request_from_call_stack() is something_else


def test_request_is_found_in_a_calling_frame(request_util):
    def inner():
        return request_util.get_request_from_call_stack()

    request = FakeRequest()

    assert inner() is request


def test_request_of_the_wrong_type_is_ignored(request_util):
    request = object()  # noqa: F841 - a "request" local that is not a request

    assert request_util.get_request_from_call_stack() is None


def test_exception_text_is_used_when_there_is_no_exc_info():
    from json_logging.formatters import JSONLogFormatter

    record = logging.LogRecord("exc-text-test", logging.ERROR, __file__, 1, "boom", None, None)
    record.exc_text = "cached traceback"

    fields = JSONLogFormatter().get_exc_fields(record)

    assert fields["exc_info"] == "cached traceback"
    assert fields["filename"] == record.filename
