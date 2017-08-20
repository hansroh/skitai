from aquests.lib.athreads import fifo
from aquests.protocols.http2 import fifo as fifo2

from confutil import rprint
import time
import random

class simple_producer:
	def __init__ (self, stream_id, weight = 0, depends_on = 0):
		pass

class producer:
	def __init__ (self, stream_id, weight = 0, depends_on = 0):
		self.stream_id = stream_id
		self.weight = weight
		self.depends_on = depends_on
	
class async_producer (producer):
	def __init__ (self, stream_id, weight = 0, depends_on = 0):
		producer.__init__ (self, stream_id, weight, depends_on)
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
	for i in range (1, num * 2 + 1, 2):
		if i < 2:
			depends_on = 0
		else:
			depends_on = random.choice ([0, random.randrange (1, i-1, 8)])	
			if depends_on % 3 == 0:
				depends_on = 0				
		f.append (producers [i % 3] (i, random.randrange (10), depends_on))

TESTS = 1000
		
def assert_fifo (f):
	fill (f, TESTS)
	loop = 0
	while f:
		first = f [0]
		#rprint (first)
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
		assert assert_fifo (fifo.await_fifo ()) < TESTS * 2.5
		assert assert_fifo (fifo.await_ts_fifo ()) < TESTS * 2.5
		assert assert_fifo (fifo2.http2_producer_fifo ()) < TESTS * 2.5
		assert assert_fifo (fifo2.http2_producer_ts_fifo ()) < TESTS * 2.5
		
		# priority sorting test
		f = fifo2.http2_producer_fifo ()
		fill (f, TESTS)
		
		streams = []
		prev_weight = 100000000
		prev_depends_on = 0
		for p in f:
			if not hasattr (p, 'stream_id'):
				continue
			else:		
				streams.append (p.stream_id)
				#rprint (p.stream_id, p.depends_on, p.weight)		
				if p.depends_on:
					assert p.depends_on in streams									
				if prev_depends_on != p.depends_on:
					prev_weight = 100000000
					prev_depends_on = p.depends_on
				else:
					assert p.weight <= prev_weight
				
					