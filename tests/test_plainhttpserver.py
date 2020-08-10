import unittest
import logging
import requests
import concurrent.futures
import json_logging
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from typing import Any
from json import loads
from io import StringIO


def setup_b3_logging(httpd: HTTPServer, level=logging.INFO):
    # enable b3-propagation
    # https://github.com/thangbn/json-logging-python#3-configuration
    json_logging.init_plain_http_server(enable_json=True)
    json_logging.init_request_instrument(httpd)

    logging.basicConfig(level=level)
    json_logging.config_root_logger()
    logging.getLogger("plain-http-request-logger").setLevel(logging.WARNING)


class RequestHandler(BaseHTTPRequestHandler):
    # override default 'Server' HTTP header
    server_version = "HTTPServer/0.1"
    logger = logging.getLogger("RequestHandler")

    # drop all msg not >= error
    def log_message(self, _: str, *args: Any) -> None:
        pass

    # redirect error msgs from stderr to our loggedr
    def log_error(self, fmt: str, *args: Any) -> None:
        self.logger.error("%s - - [%s] %s\n" %
                          (self.address_string(),
                           self.log_date_time_string(),
                           fmt % args))

    def do_GET(self):
        self.transaction = transaction = json_logging.framework.plainhttpserver.PlainHTTPResponse()
        if hasattr(self.server, 'attach_req_info_to_response'):
            self.server.attach_req_info_to_response(transaction, self.path, self.request, self.headers)

        # call actual backend functionality
        self.some_fancy_backend_functionality()

        # Build response
        self.send_response(transaction.status)
        self.send_header('Content-Type', transaction.content_type)
        self.end_headers()
        self.wfile.write(transaction.content)

        if transaction.request_info is not None:
            self.server.after_request(transaction)
        return

    def some_fancy_backend_functionality(self):
        # there's no further logging, so let's emit someting
        self.logger.info(f"called path:{self.path}")
        self.transaction.status = 200
        self.transaction.content = bytes("Hello world!", "utf-8")


def setup_http_server(server_address=('', 8006)):
    httpd = HTTPServer(server_address, RequestHandler)
    setup_b3_logging(httpd)
    return httpd


class ServiceResolverE2E(unittest.TestCase):
    server_port = 12345
    logger = logging.getLogger("testenv")
    default_x_headers = {
        "X-Forwarded-For": "1.2.3.4",
        "X-Correlation-ID": "mock-corr-id",
        "X-Request-ID": "mock-req-id"}
    # must only initialized once (because of the python-instance wide logger setup)
    httpd = setup_http_server(server_address=('', server_port))

    @staticmethod
    def print_logger() -> None:
        for k, v in logging.Logger.manager.loggerDict.items():
            print('+ [%s] {%s} ' % (str.ljust(k, 20), str(v.__class__)[8:-2]))
            if isinstance(v, logging.PlaceHolder):
                continue
            for h in v.handlers:
                print('     +++', str(h.__class__)[8:-2])

    def setUp(self):
        logging.basicConfig(level=logging.INFO)

        # redirect the json_logger output to our StringIO Stream i.o to
        #   check the outcome later on.
        self.string_stream = string_stream = StringIO()
        json_handler = [each for each in logging.getLogger().handlers
                        if isinstance(each.formatter, json_logging.JSONLogWebFormatter)]
        for each in json_handler:
            each.stream = string_stream

        # ServiceResolverE2E.print_logger()

    def _request_n_shutdown(self, *args, **kwargs):
        res = requests.get(*args, **kwargs)
        self.httpd.shutdown()
        return res

    def test_request(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            fqdn = f"http://localhost:{self.server_port}/foobar"
            future = executor.submit(self._request_n_shutdown, fqdn, headers=self.default_x_headers)

            self.httpd.serve_forever()
        return_value = future.result()
        logged_string = self.string_stream.getvalue()
        print(logged_string)

        expected_log_results = {"correlation_id": self.default_x_headers.get('X-Correlation-ID'),
                                "msg": "called path:/foobar"}
        # <= ..  true only if `first` is a subset of `second`
        self.assertTrue(expected_log_results.items() <= loads(logged_string).items())
        self.assertEqual(200, return_value.status_code)
        self.assertEqual("Hello world!", return_value.text)
