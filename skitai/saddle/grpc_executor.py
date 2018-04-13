from . import wsgi_executor
try:
	import xmlrpc.client as xmlrpclib
except ImportError:
	import xmlrpclib
import sys, os
import struct
import asynchat
import threading
import copy
from aquests.protocols.grpc.producers import grpc_producer
from aquests.protocols.grpc.discover import find_input
from aquests.lib.athreads import trigger
from skitai.server.handlers import collectors	
from skitai import version_info, was as the_was

class Executor (wsgi_executor.Executor):
	def __init__ (self, env, get_method):	
		wsgi_executor.Executor.__init__ (self, env, get_method)
		self.producer = None
		self.service = None
		self.num_streams = 0
				
	def __call__ (self):
		request = self.env ["skitai.was"].request
		collector = request.collector
		data = self.env ["wsgi.input"]
		self.input_type = find_input (request.uri [1:])
			
		servicefullname = self.env ["SCRIPT_NAME"][1:-1]
		methodname = self.env ["PATH_INFO"]		
		sfn = servicefullname. split (".")		
		packagename = ".".join (sfn [:-1])
		servicename = sfn [-1]		
		
		current_app, self.service, param, respcode = self.find_method (request, methodname, True)		
		if respcode:
			return b""
			
		self.build_was ()
		self.was.subapp = current_app
		self.was.response ["grpc-accept-encoding"] = 'identity,gzip'
		self.was.response.set_trailer ("grpc-status", "0")
		self.was.response.set_trailer ("grpc-message", "ok")
		
		descriptor = []
		for m in data:
			f = self.input_type [0]()
			f.ParseFromString (m)
			descriptor.append (f)
		if not self.input_type [1]: # not stream
			descriptor = descriptor [0]

		result = b""
		try:
			result = self.chained_exec (self.service, (descriptor,), {})
			
		except:
			self.was.traceback ()			
			self.was.response.set_trailer ("grpc-status", "2")
			self.was.response.set_trailer ("grpc-message", "internal error")		
			self.rollback ()
			
		else:
			if result:
				self.was.response ["content-type"] = "application/grpc"
			self.commit ()
			result = grpc_producer (result [0], False)
			for k,v in result.get_headers ():
				self.was.response [k] = v
			
		del self.was.subapp
		del self.was.env
		
		return result
				
		