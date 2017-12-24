# coding=utf-8
class RequestAdapter:
    """
        Helper class help to extract logging-relevant information from HTTP request object
    """

    def __new__(cls, *arg, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = object.__new__(cls)
        return cls._instance

    @staticmethod
    def support_global_request_object():
        """
            whether current framework supports global request object
        """
        raise NotImplementedError

    @staticmethod
    def get_current_request():
        """
            get current request, should only implement for framework that support global request object
        """
        raise NotImplementedError

    @staticmethod
    def get_request_class_type():
        """
            class type of request object
        """
        raise NotImplementedError

    def get_http_header(self, request, header_name, default=None):
        """
        get HTTP header value given it value name

        :param request: request object
        :param header_name: name of header
        :param default: default value if header value is not present
        :return:
        """
        raise NotImplementedError

    def get_remote_user(self, request):
        """

        :param request: request object
        """
        raise NotImplementedError

    def is_in_request_context(self, request):
        """

        :param request: request object
        """
        raise NotImplementedError

    def set_correlation_id(self, request, value):
        """
        We can safely assume that request is valid request object.\n
        Set correlation to request context. e.g Flask.g in Flask
        Made sure that we can access it later from get_correlation_id_in_request_context given the same request.

        :param value: correlation id string
        :param request: request object
        """
        raise NotImplementedError

    def get_correlation_id_in_request_context(self, request):
        """
        We can safely assume that request is valid request object.

        :param request: request object
        """
        raise NotImplementedError

    def get_protocol(self, request):
        """
        We can safely assume that request is valid request object.\n
        Gets the request protocol (e.g. HTTP/1.1).

        :return: The request protocol or '-' if it cannot be determined
        """
        raise NotImplementedError

    def get_path(self, request):
        """
        We can safely assume that request is valid request object.\n
        Gets the request path.

       :return: the request path (e.g. /index.html)
        """
        raise NotImplementedError

    def get_content_length(self, request):
        """
        We can safely assume that request is valid request object.\n
        The content length of the request.

        :return: the content length of the request or '-' if it cannot be determined
        """
        raise NotImplementedError

    def get_method(self, request):
        """
        We can safely assume that request is valid request object.\n
        Gets the request method (e.g. GET, POST, etc.).

        :return: The request method or '-' if it cannot be determined
        """
        raise NotImplementedError

    def get_remote_ip(self, request):
        """
        We can safely assume that request is valid request object.\n
        Gets the remote ip of the request initiator.

        :return: An ip address or '-' if it cannot be determined
        """
        raise NotImplementedError

    def get_remote_port(self, request):
        """
        We can safely assume that request is valid request object.\n
        Gets the remote port of the request initiator.

        :return: A port or '-' if it cannot be determined
        """
        raise NotImplementedError


class ResponseAdapter:
    """
        Helper class help to extract logging-relevant information from HTTP response object
    """

    def __new__(cls, *arg, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = object.__new__(cls)
        return cls._instance

    def get_status_code(self, response):
        """
        get response's integer status code

        :param response: response object
        """
        raise NotImplementedError

    def get_response_size(self, response):
        """
        get response's size in bytes

        :param response: response object
        """
        raise NotImplementedError

    def get_content_type(self, response):
        """
        get response's MIME/media type

        :param response: response object
        """
        raise NotImplementedError


class FrameworkConfigurator:
    """
       Class to perform logging configuration for given framework as needed
    """

    def __new__(cls, *args, **kw):
        if not hasattr(cls, '_instance'):
            cls._instance = object.__new__(cls)
        return cls._instance

    def config(self):
        """
            app logging configuration logic
        """
        raise NotImplementedError


class AppRequestInstrumentationConfigurator:
    """
        Class to perform request instrumentation logging configuration. Should at least contains:
        1- register before-request hook and create a RequestInfo object, store it to request context
        2- register after-request hook and update response to stored RequestInfo object
        3 - re-configure framework loggers.
        NOTE: logger that is used to emit request instrumentation logs will need to assign to **self.request_logger**
    """

    def __new__(cls, *args, **kw):
        if not hasattr(cls, '_instance'):
            cls._instance = object.__new__(cls)
            cls._instance.request_logger = None
        return cls._instance

    def config(self, app):
        """
        configuration logic

        :param app:
        """
        raise NotImplementedError

    def get_request_logger(self):
        """
        get the current logger that is used to logger the request instrumentation information
        """
        return self.request_logger
