import re
import stat
import time
from mimetypes import types_map
import os
from . import filesys
from rs4 import producers
from rs4.termcolor import tc
from aquests.protocols.http import http_date
from aquests.protocols.http.http_util import *
from ..corequest import tasks
from aquests.athreads import trigger
from .. import utility
USER_AGENT = re.compile ('User-Agent: (.*)', re.IGNORECASE)

CONTENT_TYPE = re.compile (
	r"Content-Type: ([^;]+)((; boundary=([A-Za-z0-9'\(\)+_,./:=?-]+)$)|$)",
	re.IGNORECASE
	)

class MemCache:
	def __init__ (self):
		self.d = {}

	def read (self, path, file, etag):
		cached = self.d.get (path)
		if cached is None or cached [0] != etag:
			with open (file, "rb") as f:
				self.d [path] = (etag, f.read ())
		return self.d [path][1]


class Handler:
	directory_defaults = [
		'index.htm',
		'index.html'
		]
	_in_thread = False

	def __init__ (self, wasc, pathmap = {}, max_ages = None, alt_handlers = []):
		self.wasc = wasc

		self.memcache = MemCache ()
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
		self.wasc.logger ('server', 'directory {} mounted to {}'.format (tc.yellow (option), tc.white (alias or '/')), 'info')
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
			current_stat = self.filesystem.stat (path)
			mtime = current_stat [stat.ST_MTIME]
			file_length = current_stat [stat.ST_SIZE]
		except:
			self.handle_alternative (request)
			return

		etag = utility.make_etag ("%d:%d" % (file_length, int (mtime)))
		range_ = request.get_header ('range')
		if range_:
			if utility.is_etag_matched (request, 'if-range', etag) == 'unmatched':
				range_ = None # ignore range
			else:
				try:
					rg_start, rg_end = parse_range (range_, file_length)
				except:
					request.response.start (416)
					request.response.done()
					return

		request.response.set_etag_mtime (
			etag,
			mtime,
			file_length,
			self.max_ages and self.get_max_age (path) or 0,
			as_etag = True
		)
		self.set_content_type (path, request)

		if range_:
			request.response ['Content-Range'] = 'bytes {}-{}/{}'.format (rg_start, rg_end, file_length)
			request.response ['Content-Length'] = (rg_end - rg_start) + 1
			offset, limit = rg_start, (rg_end - rg_start) + 1
			request.response.start (206)

		else:
			request.response ['Content-Length'] = file_length
			offset, limit = 0, file_length

		if request.command == 'get' and limit:
			# if head, don't send contents
			if file_length < 4096:
				request.response.push (
					self.memcache.read (path, self.filesystem.translate (path), etag) [offset:limit]
				)
			else:
				request.response.push (producers.file_producer (
					self.filesystem.open (path, 'rb'), proxsize = file_length, offset = offset, limit = limit)
				)

		if self._in_thread:
			trigger.wakeup (lambda p = request.response: (p.done (),))
		else:
			request.response.done()

	def get_max_age (self, path):
		path = not path and "/" or "/" + path
		for prefix, value in self.max_ages:
			if path.startswith (prefix):
				return value

	def set_content_type (self, path, request):
		ext = get_extension (path).lower()
		request.response['Content-Type'] = types_map.get ("." + ext, 'application/octet-stream')

	def get_static_files (self):
		return StaticFiles (self.wasc, self.filesystem, self.max_ages, self.memcache)


class StaticFiles (Handler):
	_in_thread = True
	__name__ = 'StaticFiles' # django make error, why?
	def __init__ (self, wasc, filesystem, max_ages, memcache):
		self.wasc = wasc
		self.filesystem = filesystem
		self.max_ages = max_ages
		self.memcache = memcache

	def handle_alternative (self, request):
		request.response.error (404)

	def __call__ (self, request, uri):
		request._split_uri = (uri,) + request._split_uri [1:]
		self.handle_request (request)
		return tasks.Revoke ()

