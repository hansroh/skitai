from ...protocols.sock.impl.http import response as http_response, buffers
from rs4.misc import compressors
from ...protocols.threaded import trigger
import time

class ProxyResponse (http_response.Response):
	SIZE_LIMIT = 2**24

	def __init__ (self, request, header, accept_gzip, client_request, asyncon):
		self.client_request = client_request
		self.asyncon = asyncon
		self.accept_gzip = accept_gzip
		self.request = request
		self.header_s = header
		if header [:2] == "\r\n":
			header = header [2:]
		header = header.split ("\r\n")
		self.response = header [0]
		self.header = header [1:]
		self._header_cache = {}
		self.flushed_time = 0
		self.mcl = self.get_mcl ()
		self.version, self.code, self.msg = http_response.crack_response (self.response)
		self.p, self.u = None, None
		self.decompressor = None
		self.gzip_compressed = False
		self.is_xmlrpc_return = False
		self.make_decompressor = False

		content_encoding = self.get_header ("Content-Encoding")
		if content_encoding == "gzip":
			if self.accept_gzip:
				self.gzip_compressed = True
			else:
				self.make_decompressor = True

		self.size = 0
		self.got_all_data = False
		self.set_max_age ()

	def body_expected (self):
		cl = self.get_header ("Content-Length")
		if cl == 0:
			self.got_all_data = True
			return False

		te = self.get_header ("Transfer-Encoding")
		if cl is None and te != "chunked":
			hv = self.version
			cn = self.get_header ("Connection")
			if cn is None:
				if hv == "1.0": cn = "close"
				else: cn = "keep-alive"
			else:
				cn = cn.lower ()
			if cn == "keep-alive":
				self.got_all_data = True
				return False

		if self.p is None:
			self.p, self.u = buffers.getfakeparser (buffers.list_buffer, cache = self.max_age)
			if self.make_decompressor:
				self.decompressor = compressors.GZipDecompressor ()

		return True

	def get_header_lines (self):
		return self.header

	def init_buffer (self):
		# do this job will be executed in body_expected ()
		pass

	def is_gzip_compressed (self):
		return self.gzip_compressed

	def close (self):
		# channel closed and called automatically by channel
		self.asyncon.handle_abort ()
		self.done ()
		#self.asyncon.handle_close (710, "Channel Closed")

	def get_size (self):
		return -1

	def ready (self):
		#print ('====== READYU', len (self.u), self.got_all_data)
		return len (self.u) or self.got_all_data

	def exhausted (self):
		return len (self.u) == 0 and self.got_all_data

	def more (self):
		self.flushed_time = time.time ()
		data = self.u.read ()
		#print ('-----', data [:70])
		return data

	def collect_incoming_data (self, data):
		http_response.Response.collect_incoming_data (self, data)
