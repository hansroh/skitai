import json
import sys
from datetime import date
from xmlrpc import client
from ..utility import catch
	
class DateEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, date):
			return str(obj)			
		return json.JSONEncoder.default(self, obj)
		
			
class API:
	def __init__ (self, request, data = None):
		self.request = request # for response typing 
		self.data = data or {}
		self.content_type = self.set_content_type ()
		
	def __setitem__ (self, k, v):
		self.set (k, v)
	
	def __getitem__ (self, k, v = None):
		return self.get (k, v)
	
	def set (self, k, v):
		self.data [k] = v
	
	def get (self, k, v = None):
		return self.data.get (k, )
	
	def get_content_type (self):
		return self.content_type
		
	def set_content_type (self):
		content_type = self.request.get_header ("accept", 'application/json')
		if not content_type.startswith ("text/xml"):			
			content_type = 'application/json'
		return content_type	
		
	def encode (self, charset):
		return self.to_string ().encode (charset)
	
	def __str__ (self):
		return self.to_string ()
		
	def to_string (self):
		if self.content_type.startswith ("text/xml"):
			return client.dumps ((self.data,))
		return json.dumps (self.data, cls = DateEncoder, ensure_ascii = False, indent = 2)
			
	def traceback (self, message = 'exception occured', code = 20000, debug = 'see traceback', more_info = None):
		self.error (message, code, debug, more_info, sys.exc_info ())
		
	def error (self, message, code = 20000, debug = None, more_info = None, exc_info = None):
		self.data = {}
		self.data ['code'] = code
		self.data ['message'] = message
		if debug:
			self.data ['debug'] = debug
		if more_info:
			self.data ['more_info'] = more_info
		if exc_info:
			self.data ["traceback"] = type (exc_info) is tuple and catch (2, exc_info) or exc_info
