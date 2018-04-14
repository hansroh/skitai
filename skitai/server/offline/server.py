
from ..wastuff import triple_logger
from ..http_server import http_server
from ..handlers import pingpong_handler
from ..handlers import vhost_handler
from ..handlers import proxy_handler
from aquests.protocols.http import response

def clear_handler (wasc):
    # reset handler
    wasc.httpserver.handlers = []
 
def handle_request (handler, request):
    assert handler.match (request)    
    handler.handle_request (request)
    if request.command in ('post', 'put', 'patch'):
        request.collector.collect_incoming_data (request.payload)
        request.collector.found_terminator ()            
    result = request.channel.socket.getvalue ()
    try:
        header, payload = result.split (b"\r\n\r\n", 1)
    except ValueError:
        raise ValueError (str (result))    
    resp = response.Response (request, header.decode ("utf8"))
    resp.collect_incoming_data (payload)    
    return resp
   
def install_vhost_handler (wasc, apigateway = 0, apigateway_authenticate = 0):
    clear_handler (wasc)            
    static_max_ages = {"/img": 3600}    
    enable_apigateway = apigateway
    apigateway_authenticate = apigateway_authenticate 
    apigateway_realm = "Pytest"
    apigateway_secret_key = "secret-pytest"    
    
    vh = wasc.add_handler (
        1, 
        vhost_handler.Handler, 
        wasc.clusters, 
        wasc.cachefs, 
        static_max_ages,
        enable_apigateway,
        apigateway_authenticate,
        apigateway_realm,
        apigateway_secret_key
    )    
    return vh

def install_proxy_handler (wasc):
    clear_handler (wasc)
    h = wasc.add_handler (
        1, 
        proxy_handler.Handler, 
        wasc.clusters, 
        wasc.cachefs, 
        False
    )    
    return h

def Server (log = None):
    log = log or triple_logger.Logger ("screen", None) 
    s = http_server ('0.0.0.0', 3000, log.get ("server"), log.get ("request"))    
    s.install_handler (pingpong_handler.Handler ())
    return s

