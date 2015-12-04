from . import eurl
from . import request as http_request
from . import request_handler
from . import localstorage
from skitai.client import socketpool


def init (logger):
	socketpool.create (logger)
	localstorage.create (logger)

def close ():
	socketpool.cleanup ()


class Request (http_request.HTTPRequest):
	def __init__ (self, thing, data = {}, logger = None):
		if localstorage.localstorage is None:
			init_request (logger)
			
		if type (thing) is bytes:
			self.el = eurl.EURL (thing, data)
		else:
			self.el = thing

		http_request.HTTPRequest.__init__ (
			self, 
			self.el ["rfc"], 
			self.el ["method"].upper (), 
			headers = self.el.get_header (),
			logger = logger
			)
			
	def split (self, uri):
		return (self.el ["netloc"], self.el ["port"]), self.el ["uri"]
		
	def serialize (self):
		pass
		
	def get_auth (self):
		return self.el ["auth"]
		
	def get_data (self):
		return self.el ["http-form"]

	def get_eurl (self):
		return self.el

