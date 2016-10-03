from .. import collectors
from . import POST_MAX_SIZE


class Collector (collectors.FormCollector):
	# same as asyncon ac_in_buffer_size
	ac_in_buffer_size = 4096
	asyncon = None
	def __init__ (self, handler, request):
		self.handler = handler
		self.request = request
		self.data = []
		self.cache = []
		self.cached = False
		self.got_all_data = False
		self.length = 0 
		self.content_length = self.get_content_length ()
	
	def reuse_cache (self):
		self.data = self.cache + self.data
		self.cache = []
			
	def start_collect (self):	
		if self.content_length == 0:
			return self.found_terminator ()
			
		if self.content_length <= POST_MAX_SIZE: #5M
			self.cached = True
		
		self.request.channel.set_terminator (self.content_length)
	
	def close (self):
		# channel disconnected
		self.data = []
		self.cache = []
		self.request.collector = None
		
		# abort immediatly
		if self.asyncon:
			self.asyncon.handle_close (710, "Channel Closed")
				
	def collect_incoming_data (self, data):
		#print "proxy_handler.collector << %d" % len (data), id (self)
		self.length += len (data)
		self.data.append (data)

	def found_terminator (self):
		self.request.channel.set_terminator (b'\r\n\r\n')
		self.got_all_data = True
		self.request.collector = None
		# don't request.collector = None => do it at callback ()
		# because this collector will be used in Request.continue_start() later
	
	def get_cache (self):
		return b"".join (self.cache)
	
	def affluent (self):
		# if channel doesn't consume data, delay recv data		
		return len (self.data) < 1000
		
	def ready (self):
		return len (self.data) or self.got_all_data
	
	def more (self):
		if not self.data:
			return b""
						
		data = []
		tl = 0
		while self.data:
			tl += len (self.data [0])
			if tl > self.ac_in_buffer_size:
				break
			data.append (self.data.pop (0))
		
		if self.cached:			
			self.cache += data
		#print "proxy_handler.collector.more >> %d" % tl, id (self)
		return b"".join (data)
		