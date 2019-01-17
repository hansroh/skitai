from skitai.wastuff import promise
from confutil import rprint
import time
import random
import pytest
from mock import MagicMock

def handler (promise, resp):
	assert promise.fulfilled ()
	assert not promise.settled ()
	assert not promise.ready ()
	promise ["b"] == "b"
	promise.settle ()		
	assert promise.settled ()
	assert promise.ready ()	
	promise.reject ('Error')
	assert promise.rejected ()
	
def test_promise (wasc):
	p = promise.Promise (wasc (), handler, a = "a")
	assert p ["a"] == "a"
	p._numreq = 1
	p (MagicMock ())
	
