
class Application:
	def __init__ (self, module, app):
		self.module = module
		self.app = app
		self.devel = False
		
		try:
			self.devel = self.module.__DEBUG__
		except AttributeError:
			self.devel = self.module.__DEBUG__ = False
	
	def is_ssgi (self):
		return False
					
	def set_devel (self, flag):			
		self.devel = self.module.__DEBUG__ = flag
	
	def do_auto_reload (self):
		return self.devel
		
	def run (self, wasc, script_name, route, *args, **karg):
		self.script_name = script_name
		self.route = route
	
	def get_method (self, *args):	
		return ([None, self.app, None, None], None)