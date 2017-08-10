from skitai.server.wastuff.storage import Storage
from confutil import rprint
import time
import random
import pytest
from mock import MagicMock

def test_storage ():
	s = Storage ({"a": (100, 0)})
	assert s.get ("a") == 100
	assert s.get ("b") is None
	assert s.get ("b", 1000) == 1000
	
	s.set ("b", 200, 1)
	assert s.get ("b") == 200	
	assert "b" in s	
	time.sleep (1)
	assert s.get ("b") is None
	assert "b" not in s	
	
	s.remove ("b")
	assert s.get ("b") is None
	
	s.clear ()
	assert len (s) == 0

def test_models_in_storage (wasc):
	was = wasc ()
	was.apps = MagicMock ()
	was.setlu ('a')
	assert time.time () - was.getlu ('a') < 1
	assert was.getlu ('b') == was.init_time
	
		