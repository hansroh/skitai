import tempfile
import os

class FormCollector:
	def __init__ (self, handler, request):
		self.handler = handler
		self.request = request
		self.buffer = BytesIO ()
		self.content_length = self.get_content_length ()
		self.size = 0
	
	def get_content_length (self):
		cl = self.request.get_header ('content-length')
		if cl is not None:
			try:
				cl = int  (cl)
			except (ValueError, TypeError):
				cl = None
		return cl
		
	def start_collect (self):	
			if self.content_length == 0: 
				return self.found_terminator()
			self.request.channel.set_terminator (self.content_length)

	def collect_incoming_data (self, data):
		self.size += len (data)
		self.buffer.write (data)

	def found_terminator (self):
		# prepare got recving next request header
		self.request.collector = None  # break circ. ref
		self.request.set_body (self.data.getvalue ())
		self.request.channel.set_terminator (b'\r\n\r\n')
		self.handler.continue_request (self.request, self.buffer)
	
	def abort (self):
		self.buffer.close ()
		self.request.collector = None  # break circ. ref


class MultipartCollector (FormCollector):
	def __init__ (self, handler, request, upload_max_size):
		self.handler = handler
		self.request = request
		self.upload_max_size = upload_max_size		
		self.content_length = self.get_content_length ()
		self.buffer = tempfile.NamedTemporaryFile(delete=False)
		self.size = 0
								
	def start_collect (self):						
		if self.content_length == 0: 
			return self.found_terminator()		
		self.request.channel.set_terminator (self.content_length)
		
	def collect_incoming_data (self, data):
		self.size += len (data)
		if self.upload_max_size and self.size > self.upload_max_size:
			raise ValueError("file size is over %d MB" % (self.size/1024./1024,))
		self.buffer.write (data)
		
	def abort (self):
		self.buffer.close ()
		self.request.collector = None
				
	def found_terminator (self):
		self.buffer.close ()		
		self.handler.continue_request (self.request, open (self.buffer.name, "rb"))
		self.request.channel.set_terminator (b'\r\n\r\n')
		