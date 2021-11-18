from datetime import datetime

from json_logging import util


class RequestResponseDTOBase(dict):
    """
        Data transfer object (DTO) for request instrumentation logging
        Served as base class for any actual RequestResponseDTO implementation
    """

    def __init__(self, request, **kwargs):
        """
        invoked when request start, where to extract any necessary information from the request object
        :param request: request object
        """
        super(RequestResponseDTOBase, self).__init__(**kwargs)
        self._request = request

    def on_request_complete(self, response):
        """
        invoked when request complete, update response information into this object, must be called before invoke request logging statement
        :param response: response object
        """
        self._response = response


class DefaultRequestResponseDTO(RequestResponseDTOBase):
    """
        default implementation
    """

    def __init__(self, request, **kwargs):
        super(DefaultRequestResponseDTO, self).__init__(request, **kwargs)
        utcnow = datetime.utcnow()
        self._request_start = utcnow
        self["request_received_at"] = util.iso_time_format(utcnow)

    # noinspection PyAttributeOutsideInit
    def on_request_complete(self, response):
        super(DefaultRequestResponseDTO, self).on_request_complete(response)
        utcnow = datetime.utcnow()
        time_delta = utcnow - self._request_start
        self["response_time_ms"] = int(time_delta.total_seconds()) * 1000 + int(time_delta.microseconds / 1000)
        self["response_sent_at"] = util.iso_time_format(utcnow)
