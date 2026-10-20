"""Contract tests for custom framework integrations (README section 5)."""
import json
import logging

from helpers.handler import FormattedMessageCollectorHandler
from helpers.imports import undo_imports_from_package


def test_global_request_framework_without_active_request_logs_empty_value():
    """framework_base documents get_request_class_type() as only required for frameworks
    without a global request object, so a framework that has one and reports no current
    request must log EMPTY_VALUE instead of failing inside the formatter."""
    import json_logging
    from json_logging.framework_base import (BaseAppRequestInstrumentationConfigurator,
                                             BaseRequestInfoExtractor, BaseResponseInfoExtractor)
    from json_logging.frameworks import register_framework_support

    class RequestInfoExtractor(BaseRequestInfoExtractor):
        @staticmethod
        def support_global_request_object():
            return True

        @staticmethod
        def get_current_request():
            return None

    class AppRequestInstrumentationConfigurator(BaseAppRequestInstrumentationConfigurator):
        def config(self, app, request_response_dto_class, exclude_url_patterns=[]):
            pass

    class ResponseInfoExtractor(BaseResponseInfoExtractor):
        pass

    logger = logging.getLogger("custom-framework-test")
    handler = FormattedMessageCollectorHandler()
    logger.addHandler(handler)
    errors = []
    handler.handleError = lambda record: errors.append(record)
    try:
        register_framework_support("custom-global-request", None, AppRequestInstrumentationConfigurator,
                                   RequestInfoExtractor, ResponseInfoExtractor)
        getattr(json_logging, "__init")(framework_name="custom-global-request", enable_json=True)
        logger.warning("outside any request")
    finally:
        logger.removeHandler(handler)
        undo_imports_from_package("json_logging")

    assert errors == []
    assert [json.loads(message)["correlation_id"] for message in handler.messages] == ["-"]
