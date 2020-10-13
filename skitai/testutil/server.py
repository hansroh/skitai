from aquests.protocols.http import request, response
from aquests.protocols.ws import response as ws_response
from ..wastuff import triple_logger
from ..backbone.http_server import http_server
from ..handlers import pingpong_handler
from ..handlers.http2.response import response as http2_response
from ..backbone.http_response import http_response
from ..handlers import vhost_handler
import skitai
from .. import lifetime
from rs4 import asyncore
from atila.collectors.multipart_collector import MultipartCollector
from unittest.mock import MagicMock

def find_handler (request):
    for h in skitai.was.httpserver.handlers:
        if h.match (request):
            return h

def process_request (request, handler = None):
    handler = handler or find_handler (request)
    handler.handle_request (request)
    if request.collector and request.command in ('post', 'put', 'patch'):
        if isinstance (request.collector, MultipartCollector):
            raise TypeError ("Cannot process upload reuqest")
        request.collector.collect_incoming_data (request.payload)
        request.collector.found_terminator ()
    return request

def get_response (request, handler = None):
    # clinet request -> server response
    request = process_request (request, handler)
    return request.response

def get_client_response (request, handler = None):
    # clinet request -> process -> server response -> client response
    # this will be used by client.Client
    request = process_request (request, handler)
    while 1:
        result = request.channel.socket.getvalue ()
        if result:
            break

    try:
        header, payload = result.split (b"\r\n\r\n", 1)
    except ValueError:
        raise ValueError (str (result))
    resp = response.Response (request, header.decode ("utf8"))
    resp.collect_incoming_data (payload)
    return resp

#------------------------------------------------------------------
def Server (log = None):
    log = log or triple_logger.Logger ("screen", None)
    s = http_server ('0.0.0.0', 3000, log.get ("server"), log.get ("request"))
    s.install_handler (pingpong_handler.Handler ())
    return s

