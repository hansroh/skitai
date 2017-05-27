import zlib
import time
import os
import sys
from aquests.protocols.http import http_date, http_util
from aquests.lib.reraise import reraise 
from aquests.lib import producers, compressors
from aquests.protocols.http import respcodes
import skitai
try: 
	from urllib.parse import urljoin
except ImportError:
	from urlparse import urljoin	

UNCOMPRESS_MAX = 2048

# Default error message
DEFAULT_ERROR_MESSAGE = """<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<title>%(code)d %(message)s</title>
<style type="text/css"><!-- *{font-family:verdana,sans-serif;}body{margin:0;padding:0;background:#efefef;font-size:14px;color:#1e1e1e;} #titles{margin-left:15px;padding:10px;}#titles h1,h2{color: #000000;} #content{padding:16px 10px 30px 16px;background:#ffffff;} #error h2 {font-size: 14px;} #error h3{font-size: 13px; color: #d90000;} #error p,b,h4,li {font-size:12px;}#error h4{color: #999999;} #error li{margin-bottom: 6px;} #error .f {color:#d90000;} #error .n {color:#003366;font-weight:bold;} #error{margin:0;padding:0;} hr{margin:0;padding:0;} #error hr{border-top:#888888 1px solid;} #error li,i{font-weight:normal;}#footer {font-size:12px;padding-left:10px;} --></style>
</head>
<body>
<div id="titles"><h1>%(code)d %(message)s</h1></div>
<hr />
<div id="content">
<p>The following error was encountered while trying to retrieve the URL:</p>
<blockquote>
<div id="error"><h2>%(message)s</h2><p>%(info)s</p></div>
<a href="%(url)s">%(url)s</a>
</blockquote>
</div>
<hr />
<div id="footer">
<p>
Generated %(gentime)s by <i>Skitai App Engine</i>
</p>
</div>
</body>
</html>"""

def catch (format = 0, exc_info = None):
	if exc_info is None:
		exc_info = sys.exc_info()
	t, v, tb = exc_info
	tbinfo = []
	assert tb # Must have a traceback
	while tb:
		tbinfo.append((
			tb.tb_frame.f_code.co_filename,
			tb.tb_frame.f_code.co_name,
			str(tb.tb_lineno)
			))
		tb = tb.tb_next

	del tb
	file, function, line = tbinfo [-1]
	
	# format 0 - text
	# format 1 - html
	# format 2 - list
	if format == 1:
		buf = ["<hr><h3>%s</h3><h4>%s</h4>" % (t.__name__.replace (">", "&gt;").replace ("<", "&lt;"), v)]
		buf.append ("<b>at %s at line %s, %s</b>" % (file, line, function == "?" and "__main__" or "function " + function))
		buf.append ("<ul type='square'>")
		buf += ["<li><i>%s</i> <span class='f'>%s</span> <span class='n'><b>%s</b></font></li>" % x for x in tbinfo]
		buf.append ("</ul>")		
		return "\n".join (buf)

	buf = []
	buf.append ("%s %s" % (t, v))
	buf.append ("in file %s at line %s, %s" % (file, line, function == "?" and "__main__" or "function " + function))
	buf += ["%s %s %s" % x for x in tbinfo]
	if format == 0:
		return "\n".join (buf)
	return buf	


class http_response:
	reply_code = 200
	reply_message = "OK"
	_is_async_streaming = False
		
	def __init__ (self, request):
		self.request = request
		self.reply_headers = [
			('Server', skitai.NAME),
			('Date', http_date.build_http_date (time.time()))
		]
		self.outgoing = producers.fifo ()
		self._is_done = False
		self.stime = time.time ()
		self.htime = 0
		
	def is_async_streaming (self):
		return self._is_async_streaming
	
	def set_streaming (self):
		self._is_async_streaming = True	
	
	def is_responsable (self):
		return not self._is_done
	
	def is_done (self):	
		return self._is_done
				
	def __len__ (self):
		return len (self.outgoing)
			
	def __setitem__ (self, key, value):
		self.set (key, value)

	def __getitem__ (self, key):
		return self.get (key)
	
	def __delitem__ (self, k):
		self.delete (k)
	
	def has_key (self, key):
		key = key.lower ()
		return key in [x [0].lower () for x in self.reply_headers]		
			
	def set (self, key, value):
		self.reply_headers.append ((key, value))
		
	def get (self, key):
		key = key.lower ()
		for k, v in self.reply_headers:
			if k.lower () == key:
				return v
			
	def delete (self, key):
		index = 0
		found = 0
		key = key.lower ()
		for hk, hv in self.reply_headers:
			if key == hk.lower ():
				found = 1
				break
			index += 1
		
		if found:
			del self.reply_headers [index]
			self.delete (key)
		
	def update (self, key, value):
		self.delete (key)
		self.set (key, value)
	
	def append_header (self, key, value):
		val = self.get (key)
		if not val:
			self.set (key, value)
		else:
			self.set (key, val + ", " + value)

	def build_reply_header (self, with_header = 1):
		h = [self.response (self.reply_code, self.reply_message)]
		if with_header:
			h.extend (['%s: %s' % x for x in self.reply_headers])
		h = '\r\n'.join (h) + '\r\n\r\n'			
		return h		
	
	def get_status_msg (self, code):
		return respcodes.get (code, "Undefined Error")
		
	def response (self, code, status):	
		return 'HTTP/%s %d %s' % (self.request.version, code, status)
	
	def parse_ststus (self, status):
		try:	
			code, status = status.split (" ", 1)
			code = int (code)
		except:
			raise AssertionError ("Can't understand given status code")		
		return code, status	

	#--------------------------------------------		
	# for WSGI & Saddle Apps
	#--------------------------------------------		
	def set_reply (self, status):
		# for Saddle App
		self.reply_code, self.reply_message = self.parse_ststus (status)
	
	def get_reply (self):
		# for Saddle App
		return self.reply_code, self.reply_message
				
	def send_error (self, status, why = "", disconnect = False):
		# for Saddle App
		if not self.is_responsable ():
			raise AssertionError ("Response already sent!")
		self ["Content-Type"] = "text/html"		
		if type (why) is tuple: # render exc_info
			why = catch (1, why)			
		code, status = self.parse_ststus (status)	
		self.error (code, status, why, force_close = disconnect, push_only = True)
	
	def instant (self, status = "", headers = None):
		# instance messaging		
		if self.request.channel is None:
			return
		code, msg = self.parse_ststus (status)
		reply = [self.response (code, msg)]
		if headers:
			for header in headers:
				reply.append ("%s: %s" % header)
		self.request.channel.push (("\r\n".join (reply) + "\r\n\r\n").encode ("utf8"))
		
	def start_response (self, status, headers = None, exc_info = None):		
		# for WSGI App
		if not self.is_responsable ():
			if exc_info:
				try:
					reraise (*exc_info)
				finally:
					exc_info = None	
			else:
				raise AssertionError ("Response already sent!")		
			return
		
		code, status = self.parse_ststus (status)
		self.start (code, status, headers)
		
		if exc_info:
			# expect plain/text, send exception info to developers
			content = catch (0, exc_info)
			self.push (content)
			
		return self.push #by WSGI Spec.
	
	#----------------------------------------	
	# Internal Rsponse Methods.
	#----------------------------------------	
	def abort (self, code, status = "", why = ""):
		self.request.channel.reject ()
		self.error (code, status, why, force_close = True)
		
	def start (self, code, status = "", headers = None):
		if not self.is_responsable (): return
		self.reply_code = code
		if status: self.reply_message = status
		else:	self.reply_message = self.get_status_msg (code)			
		if headers:
			for k, v in headers:
				self.set (k, v)
	reply = start
	
	def build_default_template (self, why = ""):
		global DEFAULT_ERROR_MESSAGE
		
		return (DEFAULT_ERROR_MESSAGE % {
			'code': self.reply_code,
			'message': self.reply_message,
			'info': why,
			'gentime': http_date.build_http_date (time.time ()),
			'url': urljoin ("%s://%s/" % (self.request.get_scheme (), self.request.get_header ("host")), self.request.uri)
			})
				
	def error (self, code, status = "", why = "", force_close = False, push_only = False):
		global DEFAULT_ERROR_MESSAGE
		if not self.is_responsable (): return
		self.outgoing.clear ()
		self.reply_code = code
		if status: self.reply_message = status
		else:	self.reply_message = self.get_status_msg (code)
			
		if type (why) is tuple: # sys.exc_info ()
			why = catch (1, why)
		
		body = self.build_default_template (why).encode ("utf8")	
		self.update ('Content-Length', len(body))
		self.update ('Content-Type', 'text/html')
		self.update ('Cache-Control', 'max-age=0')
		self.push (body)
		if not push_only:
			self.done (force_close)
	
	#--------------------------------------------
	# Send Response
	#--------------------------------------------	
	def die_with (self, thing):
		if self.request.channel:
			self.request.channel.attend_to (thing)
	
	def hint_promise (self, *args, **kargs):
		# ignore in version 1.x
		pass
		
	def push (self, thing):		
		if not self.is_responsable (): 
			return
		if type(thing) is bytes:
			self.outgoing.push (producers.simple_producer (thing))
		else:			
			self.outgoing.push (thing)
	      					
	def done (self, force_close = False, upgrade_to = None, with_header = 1):
		if not self.is_responsable (): return
		self._is_done = True
		if self.request.channel is None: return
			
		self.htime = (time.time () - self.stime) * 1000
		self.stime = time.time () #for delivery time		
		
		# compress payload and globbing production
		do_optimize = True
		if upgrade_to or self.is_async_streaming ():
			do_optimize = False
						
		connection = http_util.get_header (http_util.CONNECTION, self.request.header).lower()
		close_it = False
		way_to_compress = ""
		wrap_in_chunking = False
		
		if force_close:
			close_it = True
			if self.request.version == '1.1':
				self.update ('Connection', 'close')
			else:	
				self.delete ('Connection')
				
		else:
			if self.request.version == '1.0':
				if connection == 'keep-alive':
					if not self.has_key ('content-length'):
						close_it = True
						self.update ('Connection', 'close')
					else:
						self.update ('Connection', 'keep-alive')						
				else:
					close_it = True
			
			elif self.request.version == '1.1':
				if connection == 'close':
					close_it = True
					self.update ('Connection', 'close')				
				if not self.has_key ('transfer-encoding') and not self.has_key ('content-length') and self.has_key ('content-type'):
					wrap_in_chunking = True
					
			else:
				# unknown close
				self.update ('Connection', 'close')
				close_it = True
		
		if len (self.outgoing) == 0:
			self.update ('Content-Length', "0")
			self.delete ('transfer-encoding')			
			self.delete ('content-type')
			outgoing_producer = producers.simple_producer (self.build_reply_header(with_header).encode ("utf8"))
			do_optimize = False
			
		elif len (self.outgoing) == 1 and hasattr (self.outgoing.first (), "ready"):
			outgoing_producer = producers.composite_producer (self.outgoing)
			if wrap_in_chunking:
				self.update ('Transfer-Encoding', 'chunked')
				outgoing_producer = producers.chunked_producer (outgoing_producer)
			outgoing_header = producers.simple_producer (self.build_reply_header(with_header).encode ("utf8"))
			self.request.channel.push_with_producer (outgoing_header)
			do_optimize = False
			
		elif do_optimize and not self.has_key ('Content-Encoding'):
			maybe_compress = self.request.get_header ("Accept-Encoding")
			if maybe_compress and self.has_key ("content-length") and int (self ["Content-Length"]) <= UNCOMPRESS_MAX:
				maybe_compress = ""
			
			else:	
				content_type = self ["Content-Type"]
				if maybe_compress and content_type and (content_type.startswith ("text/") or content_type.endswith ("/json-rpc")):
					accept_encoding = [x.strip () for x in maybe_compress.split (",")]
					if "gzip" in accept_encoding:
						way_to_compress = "gzip"
					elif "deflate" in accept_encoding:
						way_to_compress = "deflate"
		
			if way_to_compress:
				if self.has_key ('Content-Length'):
					self.delete ("content-length") # rebuild
				self.update ('Content-Encoding', way_to_compress)	

			if wrap_in_chunking:				
				outgoing_producer = producers.composite_producer (self.outgoing)
				self.delete ('content-length')
				self.update ('Transfer-Encoding', 'chunked')				
				if way_to_compress:
					if way_to_compress == "gzip": 
						compressing_producer = producers.gzipped_producer
					else: # deflate
						compressing_producer = producers.compressed_producer
					outgoing_producer = compressing_producer (outgoing_producer)
				outgoing_producer = producers.chunked_producer (outgoing_producer)
				outgoing_header = producers.simple_producer (self.build_reply_header(with_header).encode ("utf8"))				
				
			else:
				self.delete ('transfer-encoding')
				if way_to_compress:					
					if way_to_compress == "gzip":
						compressor = compressors.GZipCompressor ()
					else: # deflate
						compressor = zlib.compressobj (6, zlib.DEFLATED)
					cdata = b""
					has_producer = 1
					while 1:
						has_producer, producer = self.outgoing.pop ()
						if not has_producer: break
						while 1:	
							data = producer.more ()
							if not data:
								break
							cdata += compressor.compress (data)									
					cdata += compressor.flush ()					
					self.update ("Content-Length", len (cdata))
					outgoing_producer = producers.simple_producer (cdata)						
				else:
					outgoing_producer = producers.composite_producer (self.outgoing)						
				outgoing_header = producers.simple_producer (self.build_reply_header(with_header).encode ("utf8"))				
			
			outgoing_producer = producers.composite_producer (
				producers.fifo([outgoing_header, outgoing_producer])
			)

		outgoing_producer = producers.hooked_producer (outgoing_producer, self.log)		
		if do_optimize:
			outgoing_producer = producers.globbing_producer (outgoing_producer)
		
		# IMP: second testing after push_with_producer()->init_send ()
		if self.request.channel is None: return

		if upgrade_to:
			request, terminator = upgrade_to
			self.request.channel.current_request = request
			self.request.channel.set_terminator (terminator)
		else:
			# preapre to receice new request for channel
			self.request.channel.current_request = None
			self.request.channel.set_terminator (b"\r\n\r\n")
		
		# proxy collector and producer is related to asynconnect
		# and relay data with channel
		# then if request is suddenly stopped, make sure close them
		self.die_with (self.request.collector)
		self.die_with (self.request.producer)
		
		logger = self.request.logger #IMP: for  disconnect with request
		try:
			if outgoing_producer:
				self.request.channel.push_with_producer (outgoing_producer)
			if close_it:
				self.request.channel.close_when_done ()
		except:			
			logger.trace ()			
						
	def log (self, bytes):				
		self.request.channel.server.log_request (
			'%s:%d %s %s %s %s %s %d %d %s %s %s %s %s %dms %dms'
			% (
			self.request.channel.addr[0],
			self.request.channel.addr[1],			
			self.request.host or "-",
			self.request.is_promise () and "PUSH" or self.request.method,
			self.request.uri,
			self.request.version,
			self.reply_code,
			self.request.rbytes,
			bytes,
			self.request.gtxid or "-",
			self.request.ltxid or "-",
			self.request.user and '"' + self.request.user.name + '"' or "-",
			self.request.token or "-",
			self.request.user_agent and '"' + self.request.user_agent + '"' or "-",
			self.htime,
			(time.time () - self.stime) * 1000
			)
		)
		# clearing resources, back refs
		self.request.response_finished ()
	
	#---------------------------------------------
	# Used within Saddle app
	#---------------------------------------------
	
	set_header = set
	get_header = get
	del_header = delete
		
	def set_headers (self, headers):
		for k, v in headers:
			self.set (k, v)
	
	def append_headers (self, headers):
		for k, v in headers:
			self.set (k, v)		
			
	def get_hedaers (self):	
		return self.reply_headers
	
	set_status = set_reply
		
	def get_status (self):
		return "%d %s" % self.get_reply ()
					
	def __call__ (self, status = "200 OK", body = None, headers = None, exc_info = None):
		global DEFAULT_ERROR_MESSAGE
		self.start_response (status, headers)
		if not body:
			return self.build_default_template (exc_info and catch (1, exc_info) or "")
		return body
	
	