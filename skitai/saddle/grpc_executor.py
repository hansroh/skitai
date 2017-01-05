from . import wsgi_executor
try:
	import xmlrpc.client as xmlrpclib
except ImportError:
	import xmlrpclib
import sys, os
import struct
from skitai.protocol.grpc.producers import grpc_producer
from collections import Iterable


class Executor (wsgi_executor.Executor):
	def __call__ (self):
		request = self.env ["skitai.was"].request
		msgs = producers.get_messages (self.env.get ("wsgi.input"))
		servicename, methodname = self.env ["PATH_INFO"].split ("/") [-2:]
		
		self.build_was ()
		current_app, thing, param, respcode = self.find_method (request, "/" + methodname)
		if respcode: 
			return b""
		
		self.was.subapp = current_app
		result = self.generate_content (thing, msgs, {})		
		del self.was.subapp
		
		self.commit ()
		self.was.response ["Content-Type"] = "application/grpc+proto"

		del self.was.env		
		
		if type (result) is list:
			result = iter (result)		
		return grpc_producer.get_messages (result)
		
		