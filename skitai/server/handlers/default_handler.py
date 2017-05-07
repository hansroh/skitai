import re
import stat
import time
from . import mime_type_table
import os
from . import filesys
from skitai.server import http_date
from aquests.lib import producers
from aquests.protocols.http.http_util import *
from hashlib import md5

IF_MODIFIED_SINCE = re.compile (
	'If-Modified-Since: ([^;]+)((; length=([0-9]+)$)|$)',
	re.IGNORECASE
	)

IF_NONE_MATCH = re.compile (
	'If-None-Match: "?(.+?)(?:$|")',
	re.IGNORECASE
	)
	
USER_AGENT = re.compile ('User-Agent: (.*)', re.IGNORECASE)

CONTENT_TYPE = re.compile (
	r"Content-Type: ([^;]+)((; boundary=([A-Za-z0-9'\(\)+_,./:=?-]+)$)|$)",
	re.IGNORECASE
	)

class Handler:
	directory_defaults = [
		'index.htm',
		'index.html'
		]
		
	def __init__ (self, wasc, pathmap = {}, max_ages = None, alt_handlers = []):
		self.wasc = wasc
		
		self.max_ages = []
		if max_ages:
			self.max_ages = [(k, v) for k, v in max_ages.items ()]
			self.max_ages.sort (key = lambda x: len (x [0]), reverse = True)
			
		self.alt_handlers = alt_handlers
		self.permit_cache = {}
		self.filesystem = filesys.mapped_filesystem ()
		for k, v in list(pathmap.items ()):
			self.add_route (k, v)
	
	def close (self):	
		for h in self.alt_handlers:
			try: h.close ()
			except AttributeError: pass
										
	def match (self, request):
		return 1
	
	def add_route (self, alias, option):
		self.filesystem.add_map (alias, option)
	
	def handle_alternative (self, request):
		for h in self.alt_handlers:
			if h.match (request):
				try:
					h.handle_request (request)
				except:						
					self.wasc.logger.trace("server")
					try: request.response.error (500)
					except: pass
				return
		request.response.error (404)
		
	def isprohibited (self, request, path):
		dirname = os.path.split(path) [0]				
		permission = self.filesystem.get_permission (dirname)
		if not permission:
			return False								
		if not self.wasc.authorizer.has_permission (request, permission):
			return True			
		return False	
		
	def handle_request (self, request):
		if request.command not in ('get', 'head'):
			self.handle_alternative (request)
			return
		
		path, params, query, fragment = request.split_uri()
		if '%' in path:
			path = unquote (path)
		
		# return redirect
		if path == "":
			request.response['Location'] = '/'
			request.response.error (301)
			return
		
		if path.find ("./") != -1 or path.find ("//") != -1:
			request.response.error (404)
			return
				
		while path and path [0] == '/':
			path = path[1:]
		
		if self.filesystem.isdir (path):		
			if path and path[-1] != '/':
				request.response['Location'] = '/%s/' % path
				request.response.error (301)
				return
			
			found = False
			for default in self.directory_defaults:
				p = path + default
				if self.filesystem.isfile (p):
					path = p
					found = True
					break
			
			if not found:
				self.handle_alternative (request)
				return
		
		elif not self.filesystem.isfile (path):			
			return self.handle_alternative (request)
		
		if path and path [-1] == "/":
			return request.response.error (404)
					
		if self.isprohibited (request, path):
			return
		
		try:
			mtime = self.filesystem.stat (path)[stat.ST_MTIME]
			file_length = self.filesystem.stat (path)[stat.ST_SIZE]
		except:
			self.handle_alternative (request)
			return		
		
		etag = self.make_etag (file_length, mtime)		
		inm = get_header_match (IF_NONE_MATCH, request.header)
		if inm and etag == inm.group (1):
			self.set_cache_control (request, path, mtime, etag)
			request.response.start (304)
			request.response.done()
			return
			
		ims = get_header_match (IF_MODIFIED_SINCE, request.header)
		length_match = 1
		if ims:
			length = ims.group (4)
			if length:
				try:
					length = int(length)
					if length != file_length:
						length_match = 0
				except:
					pass
					
		ims_date = 0
		if ims:
			ims_date = http_date.parse_http_date (ims.group (1))

		if length_match and ims_date:
			if mtime <= ims_date:
				self.set_cache_control (request, path, mtime, etag)
				request.response.start (304)
				request.response.done()
				return
		
		try:
			file = self.filesystem.open (path, 'rb')
		except IOError:
			self.handle_alternative (request)
			return
		
		request.response ['Content-Length'] = file_length		
		self.set_cache_control (request, path, mtime, etag)
		self.set_content_type (path, request)

		if request.command == 'get':
			request.response.push (producers.file_producer (file))
			
		request.response.done()
	
	def set_cache_control (self, request, path, mtime, etag):
		max_age = self.max_ages and self.get_max_age (path) or 0
		if request.version == "1.0":			
			request.response ['Last-Modified'] = http_date.build_http_date (mtime)
			if max_age:
				request.response ['Expires'] = http_date.build_http_date (mtime + max_age)
		else:
			request.response ['Etag'] = '"' + etag + '"'
			if max_age:
				request.response ['Cache-Control'] = "max-age=%d" % max_age		
				
	def get_max_age (self, path):
		path = not path and "/" or "/" + path
		for prefix, value in self.max_ages:			
			if path.startswith (prefix):
				return value
		
	def make_etag (self, file_length, mtime):
		return md5 (("%d:%d" % (file_length, int (mtime))).encode ("utf8")).hexdigest()
	
	def set_content_type (self, path, request):
		ext = get_extension (path).lower()
		if ext in mime_type_table.content_type_map:
			request.response['Content-Type'] = mime_type_table.content_type_map[ext]
		else:
			request.response['Content-Type'] = 'text/plain'
			
