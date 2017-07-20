from aquests.lib.athreads import fifo
from aquests.protocols.http2 import fifo as fifo2

from confutil import rprint
import time
import random

class simple_producer:
	def __init__ (self, weight = 0, depends_on = 0):
		pass

class producer:
	def __init__ (self, weight = 0, depends_on = 0):
		self.weight = weight
		self.depends_on = depends_on
	
class async_producer (producer):
	def __init__ (self, weight = 0, depends_on = 0):
		producer.__init__ (self, weight, depends_on)
		self._ready = 0
	
	def rand (self):
		self._ready = random.randrange (2)
		
	def ready (self):
		if self._ready:
			return self._ready
		self._ready = random.randrange (2)
		return self._ready

def fill (f, num):
	producers = [simple_producer, producer, async_producer]	
	for i in range (num):
		f.append (producers [i % 3] (random.randrange (10), random.randrange (10)))		
		
def assert_fifo (f):
	fill (f, 300)
	loop = 0
	while f:
		first = f [0]
		print (first)
		if hasattr (first, "_ready"):			
			assert first._ready
			first.rand ()
		del f [0]
		if random.randrange (2):
			f.appendleft (first)
		loop += 1
	rprint (loop)	
	return loop		
	
def test_await_fifo ():
	for i in range (1):
		assert_fifo (fifo.await_fifo ()) < 750
		assert_fifo (fifo.await_ts_fifo ()) < 750
		
		f = fifo2.http2_producer_fifo ()
		fill (f, 100)
		initial = 0
		assert_fifo (fifo2.http2_producer_fifo ()) < 750
	