import os
from rs4 import pathtool, logger
if os.environ.get ("SKITAI_ENV") == "PYTEST":
    from threading import Lock
else:    
    from multiprocessing import Lock
    
class Logger:
	def __init__ (self, media, path):
		self.media = type (media) is list and media  or [media]		
		self.path = path
		if self.path: 
			pathtool.mkdir (path)			
		self.logger_factory = {}
		self.lock = Lock ()
		
		self.make_logger ("server", "monthly")
		self.make_logger ("app", "daily")
		self.make_logger ("request", "daily")
		
	def make_logger (self, prefix, freq = "daily"):
		self.lock.acquire ()
		has_prefix = prefix in self.logger_factory
		if has_prefix:
			self.lock.release ()
			raise TypeError("%s is already used" % prefix)
								
		_logger = logger.multi_logger ()
		if self.path and 'file' in self.media:
			_logger.add_logger (logger.rotate_logger (self.path, prefix, freq))
		if 'screen' in self.media:
			_logger.add_logger (logger.screen_logger ())
		
		self.logger_factory [prefix] = _logger
		self.lock.release ()	
	
	def add_screen_logger (self):
		for prefix, _logger in list(self.logger_factory.items ()):
			_logger.add_logger (logger.screen_logger ())
		
	def get (self, prefix):
		return self.logger_factory [prefix]
			
	def trace (self, prefix, ident = ""):
		self.get (prefix).trace (ident)		
		
	def __call__ (self, prefix, msg, log_type = ""):		
		self.get (prefix).log (msg, log_type)
	
	def rotate (self):
		self.lock.acquire ()
		loggers = list(self.logger_factory.values ())
		self.lock.release ()
		
		for mlogger in loggers:
			for logger in mlogger.loggers:
				if hasattr (logger, "rotate"):
					logger.rotate ()
		
	def close (self):
		with self.lock:
			for mlogger in self.logger_factory.values ():
				mlogger.close ()
			self.logger_factory = {}
			