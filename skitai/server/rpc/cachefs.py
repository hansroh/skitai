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

class CacheFileSystem:
	def __init__ (self, path, memmax = 64, timeout = 86400):
		self.path = path
		self.memmax = memmax * 1024 * 1024
		self.timeout = timeout
		self.files = {}
		self.hits = {}
		self.memcache = {}
		self.memusage = 0
		self.check_dir ()
		self.lock = threading.RLock ()
		self.numhits = counter.counter ()
		self.numfails = counter.counter ()
	
	def status (self):
		self.lock.acquire ()
		r = {
			"numhits": self.numhits.as_long (),
			"numfails": self.numfails.as_long (),			
			"numchachedfiles": reduce (lambda x, y: x + y, list(self.files.values ()))
		}
		self.lock.release ()
		return r

	def check_dir (self):
		for h in list(range(48,58)) + list(range(97,103)):
			for i in list(range(48,58)) + list(range(97,103)):
				for j in list(range(48,58)) + list(range(97,103)):
					initial = "0" + chr (h) + "/" + chr (i) + chr (j)
					pathtool.mkdir (os.path.join (self.path, initial))
					self.hits [initial] = 1
					self.files [initial] = 0
		
	def maintern (self, initial, force_remove = False):
		c = 0
		for path in glob.glob (os.path.join (self.path, initial, "*")):
			if force_remove or os.stat (path).st_mtime < time.time () - self.timeout:				
				os.remove (path)
			else:
				c += 1
		return c
	
	def truncate (self):
		self.lock.acquire ()
		files = list(self.files.keys ())
		self.lock.release ()
		for initial in files:
			d = self.maintern (initial, True)
			self.lock.acquire ()
			self.files [initial] = c
			self.lock.release ()
						
	def getpath (self, uri, data):
		if not data: 
			data = "" # to make standard type
		key = uri + ":" + str (data)
		file = md5 (key.encode ("utf8")).hexdigest ()
		initial = "0" + file [0] + "/" + file [1:3]
		self.hits [initial] += 1
		if self.hits [initial] % 1000 == 0:
			c = self.maintern (initial)
			self.lock.acquire ()
			self.files [initial] = c
			self.lock.release ()	
		return os.path.join (self.path, initial, file), initial
	
	def decompress (self, content_type, content):
		if content_type [:5] == "text/":
			decompressor = compressors.GZipDecompressor ()
			return decompressor.decompress (content) + decompressor.flush ()
		else:
			content	
			
	def get (self, uri, data, undecompressible = 0):		
		path, initial = self.getpath (uri, data)

		memhit = False
		try:			
			m = self.memcache [initial][path]
			memhit = True
		except KeyError:			
			if not os.path.isfile (path): 
				self.lock.acquire ()
				self.numfails.inc ()
				self.lock.release ()
				return None, None, None, None, None
		
		if memhit:
			mtime, size, max_age = m [0:3]
		else:	
			mtime = os.stat (path).st_mtime
			f = open (path, "rb")
			max_age = int (f.read (12))
		
		if os.stat (path).st_mtime < time.time () - max_age:
			if memhit:
				del self.memcache [initial][path]
				self.memusage -= (size + size * 0.2)
			else:	
				f.close ()
			self.lock.acquire ()
			self.files [initial] -= 1
			self.lock.release ()
			os.remove (path)
			return None, None, None, None, None
		
		self.lock.acquire ()	
		self.numhits.inc ()
		self.lock.release ()
		if memhit:
			compressed, content_type, content = m [3:6]
				
		else:	
			compressed = int (f.read (1))
			content_type = f.read (64).strip ().decode ("utf8")
			content = f.read ()
			f.close ()
			
			if self.memusage < self.memmax:
				size = len (content)
				self.memusage += (size + size * 0.2)
				
				try:
					self.memcache [initial]
				except KeyError:
					self.memcache [initial] = {}
						
				self.memcache [initial][path] = (
					mtime,
					size, 
					max_age,
					compressed, 
					content_type, 
					content
				)
				
		if compressed and not undecompressible:
			decompressor = compressors.GZipDecompressor ()
			content = decompressor.decompress (content) + decompressor.flush ()
			compressed = 0
		
		return memhit and 1 or -1, compressed, max_age, content_type, content
		
	def save (self, uri, data, content_type, content, max_age, compressed = 0):		
		if len (str (max_age)) > 12 or len (content_type) > 64:
			return
		
		path, initial = self.getpath (uri, data)
		if not os.path.isfile (path):
			self.lock.acquire ()
			self.files [initial] += 1
			self.lock.release ()
			f = open (path, "wb")
		else:
			return
		
		if not compressed and content_type.startswith ("text/"):
			compressor = compressors.GZipCompressor ()
			content = compressor.compress (content) + compressor.flush ()
			compressed = 1
		
		if not content_type:
			content_type = b""	
		
		f.write (("%12s%d%64s" % (max_age, compressed, content_type)).encode ("utf8"))
		f.write (content)
		f.close ()
		
		if self.memusage < self.memmax:
			size = len (content)
			self.memusage += (size + size * 0.2)
			
			try:
				self.memcache [initial]
			except KeyError:
				self.memcache [initial] = {}
					
			self.memcache [initial][path] = (
				time.time (),
				size, 
				max_age,
				compressed, 
				content_type, 
				content
			)
			
			
if __name__ == "__main__":
	f = ReverseProxy ("g:\\ttt")
	f.save ("a", "b", "asdasda")
	print(f.get ("a", "b"))
	print(f.status ())
