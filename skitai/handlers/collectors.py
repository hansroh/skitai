import tempfile
import os
try:
	from StringIO import StringIO as BytesIO
except ImportError:
	from io import BytesIO

class FormCollector:
	def __init__ (self, handler, request, *args):
		self.handler = handler
		self.request = request
		self.buffer = BytesIO ()
		self.content_length = self.get_content_length ()
		self.size = 0
		self.max_cl = 0

	def set_max_content_length (self, max_cl):
		self.max_cl = max_cl

	def get_max_content_length (self):
		return self.max_cl

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
		if self.max_cl and self.size > self.max_cl:
			raise ValueError ("Too Large Entity")
		self.buffer.write (data)

	def found_terminator (self):
		# prepare got recving next request header
		self.request.collector = None  # break circ. ref
		self.request.channel.set_terminator (b'\r\n\r\n')

		body = self.buffer.getvalue ()
		if body:
			self.request.set_body (body)
			self.buffer.seek (0)
			self.handler.continue_request (self.request, self.buffer)
		else:
			self.handler.continue_request (self.request, None)

	def close (self):
		self.buffer.close ()
		self.request.collector = None  # break circ. ref


class HTTP2DummyCollector (FormCollector):
	def __init__ (self, handler, request, respcode):
		self.handler = handler
		self.request = request
		self.respcode = respcode
		self.content_length = self.get_content_length ()
		self.size = 0
		self.max_cl = 1048576 # allow max 1M
		if self.content_length and self.content_length > self.max_cl:
			self.finish_collect (True)

	def finish_collect (self, force_close = False):
		self.request.channel.set_terminator (9)
		self.request.collector = None  # break circ. ref
		self.handler.continue_request (self.request, None, (self.respcode, force_close))

	def collect_incoming_data (self, data):
		self.size += len (data)
		if self.max_cl and self.size > self.max_cl:
			self.finish_collect (True)

	def found_terminator (self):
		self.finish_collect ()

	def close (self):
		self.request.collector = None  # break circ. ref


class MultipartCollector (FormCollector):
	def __init__ (self, handler, request, upload_max_size, file_max_size, cache_max_size = None, *args):
		self.handler = handler
		self.request = request
		self.content_length = self.get_content_length ()
		self.buffer = tempfile.NamedTemporaryFile(delete=False)
		self.size = 0

	def start_collect (self):
		if self.content_length == 0:
			return self.found_terminator()
		self.request.channel.set_terminator (self.content_length)

	def collect_incoming_data (self, data):
		self.size += len (data)
		self.buffer.write (data)

	def close (self):
		self.buffer.close ()
		self.request.collector = None

	def found_terminator (self):
		self.buffer.close ()
		self.handler.continue_request (self.request, open (self.buffer.name, "rb"))
		self.request.channel.set_terminator (b'\r\n\r\n')
