from . import http_response, counter
import re

class http_request:
	version = "1.1"
	collector = None
	producer = None
	request_count = counter.counter()
	
	def __init__ (self, *args):
		self.request_number = self.request_count.inc()		
		(self.channel, self.request,
		 self.command, self.uri, self.version,
		 self.header) = args
		self.logger = self.channel.server.server_logger
		self.server_ident = self.channel.server.SERVER_IDENT		
		self.body = None
		self.reply_code = 200
		self.reply_message = ""		
		self.loadbalance_retry = 0
		self.rbytes = 0
		self.gzip_encoded = False
		self.is_promise = False
		
		self._split_uri = None
		self._header_cache = {}

		self.set_log_info ()
		self.response = http_response.http_response (self)
	
	def set_log_info (self):
		self.gtxid = self.get_header ("X-Gtxn-Id")
		if not self.gtxid:
			self.gtxid = "gtid-%s-c%s-r%s" % (
				self.channel.server.hash_id,
				self.channel.channel_number, 
				self.request_count
			)
			self.ltxid = 1000
		else:			
			self.ltxid = self.get_header ("X-Ltxn-Id")
			if not self.ltxid:
				raise ValueError ("Local txn ID missing")
			self.ltxid = int (self.ltxid) + 1000
			
		self.token = None
		self.claim = None
		self.user = None		
		self.host = self.get_header ("host")
		self.user_agent = self.get_header ("user-agent")
	
	def get_gtxid (self):
		return self.gtxid
		
	def get_ltxid (self, delta = 1):
		self.ltxid += delta
		return str (self.ltxid)
			
	def get_scheme (self):	
		from .https_server import https_channel		
		return isinstance (self.channel, https_channel) and "https" or "http"
	
	def get_raw_header (self):
		return self.header
	get_headers = get_raw_header
	
	path_regex = re.compile (r'([^;?#]*)(;[^?#]*)?(\?[^#]*)?(#.*)?')
	def split_uri (self):
		if self._split_uri is None:
			m = self.path_regex.match (self.uri)
			if m.end() != len(self.uri):
				raise ValueError("Broken URI")
			else:
				self._split_uri = m.groups()				
		return self._split_uri

	def get_header_with_regex (self, head_reg, group):
		for line in self.header:
			m = head_reg.match (line)
			if m.end() == len(line):
				return head_reg.group (group)
		return ''
	
	def set_body (self, body):
		self.body = body
	
	def get_body (self):
		return self.body
	
	def set_header (self, name, value):
		self.header.append ("%s: %s" % (name, value))		
		
	def get_header (self, header = None, default = None):
		if header is None:
			return self.header
		header = header.lower()
		hc = self._header_cache
		if header not in hc:
			h = header + ':'
			hl = len(h)
			for line in self.header:
				if line [:hl].lower() == h:
					r = line [hl:].strip ()
					hc [header] = r
					return r
			hc [header] = None
			return default
		else:
			return hc[header] is not None and hc[header] or default
	
	def get_header_with_attr (self, header, default = None):
		d = {}
		v = self.get_header (header, default)
		if v is None:
			return default, d
			
		v2 = v.split (";")
		if len (v2) == 1:
			return v, d
		for each in v2 [1:]:
			try:
				a, b = each.strip ().split ("=", 1)
			except ValueError:
				a, b = each.strip (), None
			d [a] = b
		return v2 [0], d	
	
	def get_content_length (self):
		try: return int (self.get_header ("content-length"))
		except ValueError: return None
					
	def get_content_type (self):
		return self.get_header_with_attr ("content-type") [0]
				
	def get_main_type (self):
		ct = self.get_content_type ()
		if ct is None:
			return
		return ct.split ("/", 1) [0]
	
	def get_sub_type (self):
		ct = self.get_content_type ()
		if ct is None:
			return
		return ct.split ("/", 1) [1]
		
	def get_user_agent (self):
		return self.get_header ("user-agent")
	
	def get_remote_addr (self):
		return self.channel.addr [0]
			
	def collect_incoming_data (self, data):
		if self.collector:
			self.rbytes += len (data)
			self.collector.collect_incoming_data (data)			
		else:
			self.logger.log (
				'dropping %d bytes of incoming request data' % len(data),
				'warning'
				)

	def found_terminator (self):		
		if self.collector:
			self.collector.found_terminator()			
		else:
			self.logger.log (
				'unexpected end-of-record for incoming request',
				'warning'
				)
			