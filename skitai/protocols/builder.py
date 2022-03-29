from .sock.impl.http import request as http_request, request_handler as http_request_handler
from .sock.impl.ws import request_handler as ws_request_handler, request as ws_request
from .sock.impl.grpc import request as grpc_request
from .sock.impl.proxy import tunnel_handler
from .sock.impl.http import localstorage as ls, util
from rs4.attrdict import AttrDict

class _Method:
	def __init__(self, send, name):
		self.__send = send
		self.__name = name

	def __getattr__(self, name):
		return _Method(self.__send, "%s.%s" % (self.__name, name))

	def __call__(self, *args):
		return self.__send(self.__name, args)


class Proxy:
	def __init__ (self, command, executor, *args, **kargs):
		self.__command = command
		self.__executor = executor
		self.__args = args
		self.__kargs = kargs

	def __getattr__ (self, name):
		return _Method(self.__request, name)

	def __request (self, method, params):
		self.__executor (self.__command, method, params, *self.__args, **self.__kargs)


class HTTPResponse:
	def __init__ (self, response):
		self.response = response
		self.request = response.request

	def __del__ (self):
		self.response.request = None
		self.request = None
		self.response = None

	def __getattr__ (self, name):
		return getattr (self.response, name)

def make_ws (_method, url, params, auth, headers, meta, proxy, logger):
    req = ws_request.Request (url, params, headers, auth, logger, meta)
    if proxy:
        if _method == 'wss':
            handler_class = tunnel_handler.WSSSLProxyTunnelHandler
        else:
            handler_class = tunnel_handler.WSProxyTunnelHandler
    else:
        handler_class = ws_request_handler.RequestHandler
    req.handler = handler_class
    return req

def make_http (_method, url, params, auth, headers, meta, proxy, logger):
    headers = util.normheader (headers)
    if ls.g:
        headers ['Cookie'] = ls.g.get_cookie_as_string (url)
    if proxy and url.startswith ('https://'):
        handler_class = tunnel_handler.SSLProxyTunnelHandler
    else:
        handler_class = http_request_handler.RequestHandler

    if _method == "rpc":
        rpcmethod, params = params
        req = http_request.XMLRPCRequest (url, rpcmethod, params, headers, auth, logger, meta)

    elif _method == "jsonrpc":
        rpcmethod, params = params
        req = http_request.JSONRPCRequest (url, rpcmethod, params, headers, auth, logger, meta)

    elif _method == "grpc":
        rpcmethod, params = params
        req = grpc_request.GRPCRequest (url, rpcmethod, params, headers, auth, logger, meta)

    elif _method == "upload":
        req = http_request.HTTPMultipartRequest (url, "POST", params, headers, auth, logger, meta)

    else:
        ct, ac = "application/x-www-form-urlencoded", "*/*"
        if _method.endswith ("json"):
            _method = _method [:-4]
            ct, ac = "application/json", "application/json"
        util.set_content_types (headers, params, (ct, ac))
        req = http_request.HTTPRequest (url, _method.upper (), params, headers, auth, logger, meta)

    req.handler = handler_class
    return req
