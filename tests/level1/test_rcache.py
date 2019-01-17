from skitai.rpc import rcache
from confutil import rprint
import time
import random
import pytest
from mock import MagicMock

def test_rcache ():
	rcache.start_rcache (100)
	rc = rcache.the_rcache
	
	r = rcache.Result (2, "A")
	assert not r.is_normal ()
	assert r.get_status () == 2
	r = rcache.Result (3, "A")
	assert r.is_normal ()
	
	r.cache (2)	
	assert len (rc) == 1
	assert r.is_cached
	assert time.time () - r.cached_time <= 2
	assert r == rc.get ("A")	
	r.cache (0)
	assert len (rc) == 0	
	r.cache (1)
	time.sleep (1.1)
	assert rc.get ("A")	is None
	
	for i in range (100):
		r = rcache.Result (2, "A")
		r.cache (1)
	assert len (rc) == 0
	
	for i in range (100):
		r = rcache.Result (3, "A")
		r.cache (1)
	assert len (rc) == 1
	
	for i in range (99):
		r = rcache.Result (3, str (i))
		r.cache (1)
	assert len (rc) == 100
	for i in range (99):
		assert rc.get (str (i))
		
	r = rcache.Result (3, "100")
	r.cache (1)
	assert len (rc) == 81
	
	for i in range (99):
		r = rcache.Result (3, str (i))
		r.cache (1)
	assert 80 <= len (rc) < 101
	
	time.sleep (1.1)
	for i in range (99):
		assert rc.get (str (i)) is None
	
	r = rcache.Result (3, "B")
	r.cache (86400)
	assert rc.get ("B")
	assert rc.get ("B", time.time () + 1) is None
	
	