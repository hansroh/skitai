from . import response
import urllib.request, urllib.parse, urllib.error
from . import eurl
from .. import socketpool, adns
from . import localstorage


def encode_form (data):
	cdata = []
	for k, v in data.itmes ():
		cdata.append ("%s=%s" % (k, urllib.parse.quote_plus (v)))
	return "&".join (cdata)

def init (logger):
	socketpool.create (logger)
	localstorage.create (logger)

def end ():
	socketpool.cleanup ()
				
			
class Request:
	keep_alive = 5
	request_timeout = 30
		
	def __init__ (self, surl, callback = None, logger = None):
		if localstorage.localstorage is None:
			init (logger)
			
		self.localstorage = localstorage.localstorage
		if type (surl) is type (""):
			self.eurl = eurl.EURL (surl)
		else:
			self.eurl = surl
			
		self.callback = callback
		self.logger = logger
		self.response = None
		self.buffer = ""
					
	def log (self, message, type = "info"):
		self.logger ("server", type, message)

	def log_info (self, message, type='info'):
		self.log (message, type)

	def trace (self):
		self.logger.trace (self.eurl ["url"])
		
	def collect_incoming_data (self, data):
		self.response.collect_incoming_data (data)
		
	def will_be_close (self):
		close_it = True
		connection = self.response.get_header ("connection")
		if self.response.version in ("1.1", "1.x"):
			if not connection or connection.lower () == "keep-alive":
				close_it = False			
		else:
			if connection and connection.lower () == "keep-alive":
				close_it = False
		return close_it
	
	def used_chunk (self):
		transfer_encoding = self.response.get_header ("transfer-encoding")
		return transfer_encoding and transfer_encoding.lower () == "chunked"
	
	def get_content_length (self):
		return int (self.response.get_header ("content-length"))
	
	def get_content_type (self):
		return self.response.get_header ("content-type")
	
	def start (self):
		adns.query (self.eurl["netloc"], "A", callback = self.continue_start)
		
	def continue_start (self, answer):
		if not answer:
			return self.handle_complete (903, "DNS Error")
		asyncon = socketpool.socketpool.get (self.eurl["proxy"] and self.eurl["proxy"] or self.eurl["netloc"], self.eurl["scheme"])
		asyncon.start_request (self)
	
	#------------------------------------------------
	# handler must provide these methods
	#------------------------------------------------
	def get_request_buffer (self):
		rh = self.eurl.make_request_header (self.localstorage)
		return rh
		
	def handle_complete (self, error, msg = "Network Error"):
		if self.response is None:
			self.response = response.FailedResponse (900, msg, self.eurl)			
		elif error:
			if self.response:
				self.response.done ()				
			self.response = response.FailedResponse (error, msg, self.eurl)
			
		if self.callback:
			self.callback (self.response)
	
	def handle_response (self, buffer):
		try:
			self.response = response.Response (self.eurl, buffer, self.localstorage)
		except:
			self.trace ()
			raise			
	
