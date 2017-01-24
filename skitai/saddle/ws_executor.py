from . import wsgi_executor
from aquests.protocols.http import respcodes
from skitai.server.http_response import catch

class Executor (wsgi_executor.Executor):
	def __call__ (self):
		request = self.env ["skitai.was"].request
		self.build_was ()	
		current_app, wsfunc = self.env.get ("websocket.handler")
		self.was.subapp = current_app
		try:
			content = wsfunc (self.was, **self.env.get ("websocket.params", {}))			
		except:
			self.rollback ()
			content = self.was.app.debug and "[ERROR] " + catch (0) or "[ERROR]"
			del self.was.env			
			del self.was.subapp
			raise			
		self.commit ()		
		# clean was
		del self.was.env		
		del self.was.subapp
		return content
