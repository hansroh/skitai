from skitai.server import counter
from skitai.lib import compressors
from hashlib import md5
from skitai.lib import pathtool
import os
import time
import threading
import glob
import threading
from functools import reduce

class CacheInfo:
	def __init__ (self):		
		self.count = 0
		self.allocated = 0.0
		self.accumulated_caches = 0
		self.accumulated_expires = 0
		
	def inc (self, delta):
		self.count += 1
		self.allocated += delta
		self.accumulated_caches += 1
		
	def dec (self, delta):
		self.count -= 1
		self.allocated -= delta
		self.accumulated_expires += 1
	
	def get (self):
		return (
			self.count, 
			self.allocated, 
			self.accumulated_caches, 
			self.accumulated_expires
		)	
		
		
class CacheFileSystem:
	maintern_interval = 600
	
	def __init__ (self, path = None, memmax = 64, diskmax = 0):
		self.path = path
		if not self.path:
			diskmax = 0
		self.max_memory = memmax * 1024 * 1024
		self.max_disk = diskmax * 1024 *1024		
		self.files = {}
		self.current_memory = CacheInfo ()
		self.current_disk = CacheInfo ()
		self.maintern_times = {}
		self.lock = threading.RLock ()		
		self.mainterns = counter.counter ()
		self.numhits = counter.counter ()
		self.numfails = counter.counter ()
		if self.max_disk:
			self.check_dir ()
	
	def status (self):
		with self.lock:
			r = {
				"numhits": self.numhits.as_long (),
				"numfails": self.numfails.as_long (),	
				'mainterned':self.mainterns.as_long (),
				"memory": self.current_memory.get (),
				"disk": self.current_disk.get ()
			}
		return r

	def check_dir (self):
		for h in list(range(48,58)) + list(range(97,103)):
			for i in list(range(48,58)) + list(range(97,103)):
				for j in list(range(48,58)) + list(range(97,103)):
					initial = "0" + chr (h) + "/" + chr (i) + chr (j)
					pathtool.mkdir (os.path.join (self.path, initial))
					self.load_cache (initial)
	
	def load_cache (self, initial, force_remove = False):
		c = 0
		current_time = time.time ()
		for path in glob.glob (os.path.join (self.path, initial, "*")):
			created = os.stat (path).st_mtime
			
			try: self.files [initial]
			except KeyError: 	self.files [initial] = {}
			
			fn = os.path.split (path)[-1]
			f = open (path, "rb")
			max_age = int (f.read (12).strip ())
			compressed = int (f.read (1).strip ())
			f.close ()
			
			if created < current_time - max_age:				
				try: os.remove (path)				
				except (OSError, IOError): pass
				continue
				
			size = os.path.getsize (path)
			self.files [initial][fn] = (created, 1, size, compressed, max_age)
			with self.lock:
				self.current_disk.inc (size)
					
	def maintern (self, initial, force_remove = False):
		current_time = time.time ()		
		valid_time = current_time - self.timeout
		deletables = []	
		for fn in self.files [initial]:
			cached = self.files [initial][fn]
			if cached [0] < valid_time or force_remove:
				deletables.append ((fn, cached [1], cached [2]))
		
		for fn, stored, usage in deletables:		
			if stored == 0:
				with self.lock:			
					self.current_memory.dec (usage)					
				del self.files [initial][fn]				
			else:	
				try: os.remove (os.path.join (self.path, initial, fn))
				except (OSError, IOError): pass
				else:	
					with self.lock:			
						self.current_disk.dec (usage)
					del self.files [initial][fn]				
		
		self.maintern_times [initial] = current_time
		with self.lock:
			self.mainterns.inc ()
			
	def truncate (self):
		for initial in self.files.keys ():
			self.maintern (initial, True)
						
	def getpath (self, key, data):
		if not data: 
			data = b"" # to make standard type		
		key = key.encode ("utf8")
		key = key + b":" + data
		file = md5 (key).hexdigest ()
		initial = "0" + file [0] + "/" + file [1:3]
		return os.path.join (self.path, initial, file), initial, file
	
	def iscachable (self, cache_control, has_cookie, has_auth, progma):
		if progma == "no-cache":			
			return False		
		if cache_control:			
			cache_control = list (map (lambda x: x.strip (), cache_control.split (",")))
			if "no-cache" in cache_control or "max-age=0" in cache_control:
				return False
			if has_auth and "public" not in cache_control:
				cachable = False
			if has_cookie and "public" not in cache_control:
				cachable = False						
		return True
					
	def get (self, key, data, undecompressible = 0):
		path, initial, fn = self.getpath (key, data)
		
		try:
			cached = self.files [initial][fn]
		except KeyError:
			with self.lock:
				self.numfails.inc ()
			return None, None, None, None, None
		
		current_time = int (time.time ())
		max_age = cached [4]
		if cached [0] < current_time - max_age:
			if cached [1] == 0:
				del self.files [initial][fn]
				with self.lock:
					self.current_memory.dec (cached [2])
			else:
				try: 
					os.remove (os.path.join (self.path, initial, fn))
				except (OSError, IOError): 
					pass
				else:
					del self.files [initial][fn]
					with self.lock:
						self.current_disk.dec (cached [2])
			return None, None, None, None, None
		
		with self.lock:
			self.numhits.inc ()
								
		if cached [1] == 0:
			content_type, content = cached [-2:]
			memhit = -1
		
		else:	
			f = open (path, "rb")
			f.read (13) # abandon max_age, compressed
			content_type = f.read (64).strip ()
			content = f.read ()
			f.close ()			
			memhit = 1
		
		compressed = cached [3]
		if compressed and not undecompressible:
			decompressor = compressors.GZipDecompressor ()
			content = decompressor.decompress (content) + decompressor.flush ()
			compressed = 0
		
		return memhit, compressed, max_age, content_type, content
	
	def save (self, key, data, content_type, content, max_age, compressed = 0):		
		if self.max_memory == 0 or not self.max_disk == 0:
			return
		usage = len (content)
		if usage > 10000000:
			return
		
		if len (str (max_age)) > 12 or len (content_type) > 64:
			return
		
		# check memory status
		with self.lock:
			current_memory = self.current_memory.get ()[1]		
			current_disk = self.current_disk.get ()[1]
		if current_memory > self.max_memory and current_disk > self.max_disk:
			# there's no memory/disk room for cache
			return self.maintern (initial)
		
		current_time = int (time.time ())
		path, initial, fn = self.getpath (key, data)
		try: self.files [initial]
		except KeyError: self.files [initial] = {}
		else:
			with self.lock:
				last_maintern = self.maintern_times.get (initial, 0.)					
			if last_maintern == 0:
				self.maintern_times [initial] = current_time
			elif current_time - last_maintern > self.maintern_interval:
				self.maintern (initial)	
		
		# already have valid cache
		cached = self.files [initial].get (fn)
		if cached: # already have
			return
			
		if not compressed and content_type.startswith ("text/"):
			compressor = compressors.GZipCompressor ()
			content = compressor.compress (content) + compressor.flush ()
			compressed = 1
			usage = len (content)
		
		if current_memory <= self.max_memory:
			usage *= 1.5
			self.files [initial][fn] = (current_time, 0, usage, compressed, max_age, content_type, content)
			with self.lock:
				self.current_memory.inc (usage)
			return
			
		f = open (path, "wb")
		if not content_type:
			content_type = b""			
		f.write (("%12s%d%64s" % (max_age, compressed, content_type)).encode ("utf8"))
		f.write (content)
		f.close ()
		self.files [initial][fn] = (current_time, 0, usage, compressed, max_age)
		with self.lock:
			self.current_disk.inc (usage)

			
if __name__ == "__main__":
	f = ReverseProxy ("g:\\ttt")
	f.save ("a", "b", "asdasda")
	print(f.get ("a", "b"))
	print(f.status ())
