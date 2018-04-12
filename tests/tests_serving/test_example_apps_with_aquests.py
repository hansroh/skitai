import confutil
from confutil import rprint
import pytest
import sys, os
import threading
import time
from examples.package import route_guide_pb2
import aquests

GRPC = 1
try:
	import grpc
except ImportError:
	GRPC = 0	

	
def start_skitai (runner, script):
	runner.start ([sys.executable, os.path.join (confutil.getroot (), script)])
	time.sleep (3)

ERRS = 0
def assert_status (resp):
	global ERRS
	if resp.status_code != resp.meta.get ("expect", 200):
		rprint (resp.status_code)
		ERRS += 1		

def makeset (https = 0, include_stream = True):
	server = (https and "https" or "http") + "://127.0.0.1:30371"
	jpg = open (os.path.join (confutil.getroot (), "statics", "reindeer.jpg"), "rb")
	
	targets = ("/", "/hello", "/redirect1", "/redirect2")
	if include_stream:
		targets += ("/documentation", "/documentation2")
	
	for url in targets:	
		aquests.get (server + url)
	aquests.get (server +"/members/", auth = ('admin', '1111'))
	aquests.post (server + "/post", {"username": "pytest"})	
	aquests.upload (server +"/upload", {"username": "pytest", "file1": jpg})	
	stub = aquests.rpc (server +"/rpc2/")
	stub.add_number (5, 7)
	if GRPC:
		stub = aquests.grpc (server +"/routeguide.RouteGuide/")
		point = route_guide_pb2.Point (latitude=409146138, longitude=-746188906)		
		stub.GetFeature (point)	

def make_stream_set (https = 0):
	server = (https and "https" or "http") + "://127.0.0.1:30371"
	aquests.get (server + "/documentation")
	aquests.get (server + "/documentation2")
		
@pytest.mark.run (order = -1)
def test_app (runner):
	global ERRS
	ERRS = 0	
	start_skitai (runner, "app.py")
	try:
		aquests.configure (2, callback = assert_status, force_http1 = True)
		[ makeset (include_stream = True) for i in range (2) ]
		aquests.fetchall ()	
		
	finally:
		runner.kill ()	
	
	assert ERRS < 4	

@pytest.mark.run (order = -1)
def test_app_h2 (runner):
	global ERRS
	
	ERRS = 0	
	start_skitai (runner, "app.py")
	try:
		aquests.configure (1, callback = assert_status)
		[ makeset (include_stream = False) for i in range (2) ]
		aquests.fetchall ()
		
	finally:
		runner.kill ()	
	
	assert ERRS < 4

@pytest.mark.run (order = -1)
def test_app_h2_streaming (runner):
	global ERRS
		
	ERRS = 0	
	start_skitai (runner, "app.py")
	try:
		aquests.configure (1, callback = assert_status)
		[ make_stream_set () for i in range (4) ]
		aquests.fetchall ()
		
	finally:
		runner.kill ()
	assert ERRS < 4

@pytest.mark.run (order = -1)
def test_https (runner):	
	global ERRS
		
	ERRS = 0
	start_skitai (runner, "https.py")
	try:
		aquests.configure (2, callback = assert_status)
		[ makeset (1) for i in range (2) ]
		aquests.fetchall ()	
	
	finally:
		runner.kill ()	
	
	assert ERRS < 4

@pytest.mark.run (order = -1)
def test_websocket (runner):
	global ERRS	
	ERRS = 0
	start_skitai (runner, "websocket.py")	
	
	try:			
		aquests.configure (1, callback = assert_status)	
		websocket = "ws://127.0.0.1:30371"
		aquests.ws (websocket + "/websocket/echo", "I'm a Websocket")			
		aquests.fetchall ()	
		
	finally:
		runner.kill ()	
	
	assert ERRS == 0

@pytest.mark.run (order = -1)
def test_dns_error (runner):
	global ERRS	
	ERRS = 0
	
	try:			
		aquests.configure (1, callback = assert_status, force_http1 = 1)	
		[ aquests.get ("http://sdfiusdoiksdflsdkfjslfjlsf.com", meta = {"expect": 704}) for i in range (3) ]
		aquests.fetchall ()	
		
	finally:
		runner.kill ()	
	
	# 100 of 7034 error
	assert ERRS == 0
		