import sys, os
try:
	from urllib.parse import unquote
except ImportError:
	from urllib import unquote	
import sys
from skitai.server import utility, http_cookie, producers
from skitai.server.http_response import catch
from skitai.server.threads import trigger
from . import collectors
import skitai
from skitai.saddle import Saddle

try:
	from cStringIO import StringIO as BytesIO
except ImportError:
	from io import BytesIO

MAX_POST_SIZE = 5242880
MAX_UPLOAD_SIZE = 2147483648
PY_MAJOR_VERSION = sys.version_info.major

header2env = {
	'content-length'	: 'CONTENT_LENGTH',
	'content-type'	  : 'CONTENT_TYPE',
	'connection'		: 'CONNECTION_TYPE'
	}
	

class Handler:
	GATEWAY_INTERFACE = 'CGI/1.1'
	ENV = {
			'GATEWAY_INTERFACE': 'CGI/1.1',
			'SERVER_SOFTWARE': "Skitai App Engine/%s.%s Python/%d.%d" % (skitai.version_info [:2] + sys.version_info[:2]),
			"wsgi.version": (1, 0),
			"wsgi.errors": sys.stderr,
			"wsgi.run_once": False,
			"wsgi.input": None
	}
		
	def __init__(self, wasc, max_file_size = 0):
		self.wasc = wasc
		self.max_file_size = max_file_size
		self.ENV ["wsgi.url_scheme"] = hasattr (self.wasc.httpserver, "ctx") == "https" or "http"
		self.ENV ["wsgi.multithread"] = hasattr (self.wasc, "threads")
		self.ENV ["wsgi.multiprocess"] = self.wasc.config.getint ("server", "processes") > 1 and os.name != "nt"
		self.use_thread = self.ENV ["wsgi.multithread"]
		
	def match (self, request):
		return 1
			
	def build_environ (self, request, app):
		(path, params, query, fragment) = request.split_uri()
		if params: path = path + params
		while path and path[0] == '/':
			path = path[1:]		
		if '%' in path: path = urllib.parse.unquote (path)			
		if query: query = query[1:]

		env = self.ENV.copy ()
		server_inst = self.wasc.httpserver
		was = self.wasc ()
		was.request = request	
		was.app = app
		env ['wsgi.x_was'] = was
		
		env ['REQUEST_METHOD'] = request.command.upper()
		env ['SERVER_PORT'] = str (server_inst.port)
		env ['SERVER_NAME'] = server_inst.server_name
		env ['SERVER_PROTOCOL'] = "HTTP/" + request.version
		env ['CHANNEL_CREATED'] = request.channel.creation_time
		if query: env['QUERY_STRING'] = query		
		env ['REMOTE_ADDR'] = request.channel.addr [0]
		env ['REMOTE_SERVER'] = request.channel.addr [0]		
		env ['SCRIPT_NAME'] = app.script_name		
		path_info = app.get_path_info ("/" + path)
		if not path_info: path_info = u"/"
		env ['PATH_INFO'] = path_info
				
		for header in request.header:
			key, value = header.split(":", 1)
			key = key.lower()
			value = value.strip ()
			if key in header2env and value:
				env [header2env [key]] = value				
			else:
				key = 'HTTP_%s' % ("_".join (key.split ( "-"))).upper()
				if value and key not in env:
					env [key] = value
		
		for k, v in list(os.environ.items ()):
			if k not in env:
				env [k] = v
		
		return env
	
	def make_collector (self, collector_class, request, max_cl = MAX_POST_SIZE, *args, **kargs):
		collector = collector_class (self, request, *args, **kargs)
		if collector.content_length is None:
			request.response.error (411)
			return
			
		elif collector.content_length > max_cl: #5M
			self.wasc.logger ("server", "too large request body (%d)" % collector.content_length, "wran")
			if request.get_header ("expect") == "100-continue":							
				request.response.error (413) # client doesn't send data any more, I wish.
			else:
				request.response.abort (413)	# forcely disconnect
			return
		
		# ok. allow form-data
		if request.get_header ("expect") == "100-continue":
			request.response.instant (100)

		return collector

	def handle_request (self, request):
		path, params, query, fragment = request.split_uri ()
		
		has_route = self.wasc.apps.has_route (path)
		if has_route == 0:
			return request.response.error (404)
					
		elif has_route == -1:
			request.response ["Location"] = "%s/%s%s" % (
				path, 
				params and params or "",
				query and query or ""
			)
			if request.command in ('post', 'put'):
				return request.response.abort (301)
			else:	
				return request.response.error (301)
		
		ct = request.get_header ("content-type")
		if request.command == 'post' and ct and ct.startswith ("multipart/form-data"):
			if isinstance (app, Saddle):
				collector = self.make_collector (collectors.SaddleMultipartCollector, request, MAX_UPLOAD_SIZE, self.max_file_size, MAX_POST_SIZE)
			else:
				collector = self.make_collector (collectors.WSGIMultipartCollector, request, MAX_UPLOAD_SIZE, MAX_UPLOAD_SIZE)	
			if collector:
				request.collector = collector
				collector.start_collect ()
			
		elif request.command in ('post', 'put'):		
			collector = self.make_collector (collectors.FormCollector, request, MAX_POST_SIZE)
			if collector:
				request.collector = collector
				collector.start_collect ()
								
		elif request.command in ('get', 'delete'):
			self.continue_request(request)
			
		else:
			request.response.error (405)
	
	def continue_request (self, request, data = None):
		try:
			path, params, query, fragment = request.split_uri ()
			app = self.wasc.apps.get_app (path)
					
		except:
			self.wasc.logger.trace ("server",  request.uri)
			return request.response.error (500, catch (1))
		
		try:
			env = self.build_environ (request, app)
			if data:
				env ["wsgi.input"] = data				
			args = (env, request.response.start_response)
								
		except:
			self.wasc.logger.trace ("server",  request.uri)
			return request.response.error (500, catch (1))
		
		if self.use_thread:
			self.wasc.queue.put (Job (request, app, args, self.wasc.logger))
		else:
			Job (request, app, args, self.wasc.logger) ()



class Job:
	def __init__(self, request, app, args, logger):
		self.request = request
		self.app = app
		self.args = args
		self.logger = logger
		
	def __repr__(self):
		return "<Job %s %s HTTP/%s>" % (self.request.command.upper (), self.request.uri, self.request.version)
	
	def __str__ (self):
		return "%s %s HTTP/%s" % (self.request.command.upper (), self.request.uri, self.request.version)
	
	def exec_app (self):
		try:			
			content = self.app (*self.args)
			
		except MemoryError:
			raise
				
		except:			
			trigger.wakeup (lambda p=self.request.response, d=catch(1): (p.error (500, d),))
		
		else:
			try:
				resp_code = self.request.response.reply_code
				if not content and resp_code >= 300:
					trigger.wakeup (lambda p=self.request.response: (p.error (resp_code),))
										
				else:	
					if not self.request.response.has_key ("content-type"):
						self.request.response.update ('Content-Type', "text/html")				
					
					type_of_content = type (content)
					if type_of_content is list:
						trigger.wakeup (lambda p=self.request.response, d=producers.list_producer (content): (p.push(d), p.done()))
					elif hasattr (content, "next"):						
						trigger.wakeup (lambda p=self.request.response, d=producers.iter_producer (content): (p.push(d), p.done()))						
					else:	
						if (PY_MAJOR_VERSION >=3 and type_of_content is str) or (PY_MAJOR_VERSION <3 and type_of_content is unicode):
							content = content.encode ("utf8")
							type_of_content = bytes
						
						if type_of_content is bytes:
							self.request.response.update ('Content-Length', len (content))			
							trigger.wakeup (lambda p=self.request.response, d=content: (p.push(d), p.done()))
				
						elif hasattr (content, "more"): # producer (ex: producers.stream_producer)
							if hasattr (content, "abort"):
								self.request.producer = content								
							trigger.wakeup (lambda p=self.request.response, d=content: (p.push(d), p.done()))
									
						else:					
							raise ValueError ("Content should be string or producer type")
								
			except:
				self.logger.trace ("app")
				trigger.wakeup (lambda p=self.request.response, d=catch(1): (p.error (500, d),))
	
	def deallocate (self):
		env = self.args [0]
		try:
			env ["wsgi.input"].close ()
		except AttributeError:
			pass
		
		try:	
			was = env ["wsgi.x_was"]
		except KeyError:
			pass
		else:		
			if hasattr (was, "cookie"): # Saddle
				was.cookie = None
				was.session = None
				was.response = None
				was.request.response = None
			was.request = None				
			was.env = None		
			was.app = None			
			del was	
								
	def __call__(self):
		try:
			self.exec_app ()
		finally:
			self.deallocate ()
		
	
			