from . import ssgi_handler
try:
	from cStringIO import StringIO as sio
	bio = sio
except ImportError:
	from io import BytesIO as bio
	from io import StringIO as sio


class Handler (ssgi_handler.Handler):
	def __init__ (self, wasc, app):
		self.app = app
		ssgi_handler.Handler.__init__ (self, wasc)

	def match (self, request):
		try:
			return self.app.match (request)
		except AttributeError:	
			return True
	
	def handle_request (self, request):
		if request.command in ('post', 'put'):
			collector = self.make_collector (Collector, request, MAX_POST_SIZE)
			if collector:
				request.collector = collector
				collector.start_collect ()
									
		elif request.command in ('get', 'delete'):
			self.continue_request(request)
			
		else:
			request.response.error (405)
				
	def continue_request (self, request, data = None):
		try:
			env = self.build_environ (request)
		except:
			self.wasc.logger.trace ("server",  request.uri)
			return request.response.error (500, catch (1))
		
		if data:
			ct = request.get_header ("content-type")
			if ct.startswith ("multipart/form-data"):
				_input = data # how to handle?
			elif ct and ct.startswith ("text/"):
				_input = sio (data)
			else:
				_input = bio (data)
			env ["wsgi.input"] = _input
			
		if self.use_thread:
			self.wasc.queue.put (Job (self.wasc, self.app, request, env))
		else:
			Job (self.wasc, self.app, request, env) ()


class Job:
	def __init__ (self, wasc, app, request, env):
		self.wasc = wasc
		self.app = app
		self.request = request
		self.env = env
		
	def __call__(self):
		try:			
			response = self.app (self.env, self.request.response.start_response)
			
		except MemoryError:
			raise
				
		except:			
			trigger.wakeup (lambda p=self.request.response, d=catch(1): (p.error (500, d),))
		
		else:		
			if not self.request.response.is_sent_response:	
				if not self.request.response.has_key ("content-type"):
					self.request.response.update ('Content-Type', "text/html")				
				
				repslen = len (responses)				
				for response in responses:
					type_of_response = type (chunk)
					if (PY_MAJOR_VERSION >=3 and type_of_response is str) or (PY_MAJOR_VERSION <3 and type_of_response is unicode):
							response = response.encode ("utf8")
							type_of_response = bytes
					
					if type_of_response is bytes:
						if repslen == 1:
							self.request.request.response.update ('Content-Length', len (response))
						self.request.reposponse.push (response)
						
					elif hasattr (response, "more"): # producer (ex: producers.stream_producer)
						if hasattr (response, "abort"):
							if repslen > 1:
								raise ValueError ("Response producer should be single")
							self.request.request.producer = response																	
						self.request.reposponse.push (response)
								
					else:
						try:
							raise ValueError("Content should be string or producer type")
						except:
							self.wasc.logger.trace ("app")						
							trigger.wakeup (lambda p=self.request.response, d=catch(1): (p.error (500, d),))
							return
						
				trigger.wakeup (lambda p=self.request.response: (p.done(),))
