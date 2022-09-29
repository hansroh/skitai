from ...backbone import http_response
from rs4.misc import producers
import time

class response (http_response.http_response):
	def __init__ (self, request):
		http_response.http_response.__init__ (self, request)
		self.trailers = []

	def set_trailer (self, name, value):
		self.trailers.append ((name, value))

	def get_trailers (self):
		return self.trailers

	def set_streaming (self):
		self._is_async_streaming = True

	def build_reply_header (self):
		h = [(b":status", str (self.reply_code).encode ("utf8"))]
		for k, v in self.reply_headers:
			h.append ((k.lower ().encode ("utf8"), str (v).encode ("utf8")))
		return h

	def push_promise (self, uri):
		if not self.request.protocol.pushable ():
			return

		host = self.request.get_header ('host', '')
		headers = [
			(':path', uri),
			(':authority', host),
			(':scheme', self.request.scheme),
			(':method', "GET")
	  	]
		additional_headers = [
	   		(k, v) for k, v in [
			   	('accept-encoding', self.request.get_header ('accept-encoding')),
			   	('accept-language', self.request.get_header ('accept-language')),
			    ('cookie', self.request.get_header ('cookie')),
			    ('user-agent', self.request.get_header ('user-agent')),
			    ('referer', "%s://%s%s" % (self.request.scheme, host, self.request.uri)),
		   ] if v
	   ]
		self.request.protocol.push_promise (self.request.stream_id, headers, additional_headers)
	hint_promise = push_promise

	def done (self, force_close = False, upgrade_to = None):
		self.content_type = self.get ('content-type')

		if not self.is_responsable (): return
		self._is_done = True
		if self.request.protocol is None: return

		self.htime = (time.time () - self.stime) * 1000
		self.stime = time.time () #for delivery time

		# removed by HTTP/2.0 Spec.
		self.delete ('transfer-encoding')
		self.delete ('connection')

		# compress payload and globbing production
		do_optimize = True
		if upgrade_to or self.is_async_streaming ():
			do_optimize = False

		if not self.outgoing:
			self.delete ('content-type')
			self.delete ('content-length')
			outgoing_producer = None

		elif len (self.outgoing) == 1 and hasattr (self.outgoing.first (), "ready"):
			outgoing_producer = producers.composite_producer (self.outgoing)
			do_optimize = False

		else:
			outgoing_producer = producers.composite_producer (self.outgoing)
			if do_optimize and not self.has_key ('Content-Encoding'):
				way_to_compress = ""
				maybe_compress = self.request.get_header ("Accept-Encoding")

				if maybe_compress:
					cl = self.has_key ("content-length") and int (self.get ("Content-Length")) or -1
					if cl == -1:
						cl = self.outgoing.get_estimate_content_length ()
					if 0 < cl <= http_response.UNCOMPRESS_MAX:
						maybe_compress = ""

				if maybe_compress:
					content_type = self.get ("Content-Type")
					if maybe_compress and content_type and (content_type.startswith ("text/") or content_type.startswith ("application/json")):
						accept_encoding = [x.strip () for x in maybe_compress.split (",")]
						if "gzip" in accept_encoding:
							way_to_compress = "gzip"
						elif "deflate" in accept_encoding:
							way_to_compress = "deflate"

				if way_to_compress:
					if self.has_key ('Content-Length'):
						self.delete ("content-length") # rebuild
					self.update ('Content-Encoding', way_to_compress)
					if way_to_compress == "gzip":
						compressing_producer = producers.gzipped_producer
					else: # deflate
						compressing_producer = producers.compressed_producer
					outgoing_producer = compressing_producer (outgoing_producer)

		if self.request.protocol is None:
			return

		if upgrade_to:
			# do not change http2 channel
			request, terminator = upgrade_to
			self.request.channel.current_request = request
			self.request.channel.set_terminator (terminator)

		try:
			self.request.protocol.handle_response (
				self.request.stream_id,
				self.build_reply_header (),
				self.get_trailers (),
				outgoing_producer,
				do_optimize,
				force_close = force_close
			)
		except:
			self.logger.trace ()
