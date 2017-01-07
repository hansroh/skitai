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
from skitai.protocol.grpc.producers import grpc_producer, grpc_stream_producer
from skitai.protocol.grpc.discover import find_input
from skitai.server.threads import trigger
from .grpc_collector import grpc_collector, grpc_stream_collector
		
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
		if not data:
			# for non-threading full-duplex stream communication
			self.was = self.was._clone ()
			
		self.was.subapp = current_app			
		self.was.response ["grpc-status"] = "0"
		self.was.response ["grpc-message"] = "ok"
		
		if not data:
			# full-duplex stream communication
			self.stream_id = self.was.request.collector.stream_id.as_long ()	
			# keep order	
			self.producer = grpc_stream_producer ()
			self.was.response.set_streaming ()
			self.was.response.push (self.producer)
			self.was.request.collector.set_service (self.producer, self.receive_stream)
			return self.producer

		descriptor = []
		for m in data:
			f = self.input_type [0]()
			f.ParseFromString (m)
			descriptor.append (f)			
		
		if not self.input_type [1]: # not stream
			descriptor = descriptor [0]			
		
		result = b""
		try:
			result = self.generate_content (self.service, (descriptor,), {})
			
		except:
			self.was.traceback ()
			self.was.response ["grpc-status"] = "2"
			self.was.response ["grpc-message"] = "internal error"
			self.rollback ()
			
		else:
			if result:
				self.was.response ["grpc-encoding"] = "gzip"		
				self.was.response ["content-type"] = "application/grpc"					
			self.commit ()

		self.close ()
		if result:
			return grpc_producer (result [0])
		return b""	
		
	def receive_stream (self, msg):
		self.num_streams += 1
		if msg is None:		
			descriptor = None
			self.commit ()
			self.close ()			
		else:
			descriptor = self.input_type [0]()
			descriptor.ParseFromString (msg)
		
		try:
			result = self.generate_content (self.service, (descriptor, self.stream_id), {})			
		except:			
			self.was.traceback ()
		else:
			if result:				
				self.producer.add_message (result [0])
		
	def close (self):
		try: self.was.request.collector.producer = None
		except AttributeError: pass	
		self.was.request.collector = None

		del self.was.subapp
		del self.was.env
		
		