import confutil
from confutil import rprint
import pytest
import sys, os
import threading
import time
from examples.services import route_guide_pb2
import aquests

GRPC = 1
try:
	import grpc
except ImportError:
	GRPC = 0	

ERRS = 0
def assert_status (resp):
	global ERRS
	if resp.status_code != resp.meta.get ("expect", 200):
		rprint (resp.status_code)
		ERRS += 1		

def makeset (https = 0, http2 = False):
	server = (https and "https" or "http") + "://127.0.0.1:30371"
	jpg = open (os.path.join (confutil.getroot (), "statics", "reindeer.jpg"), "rb")
	
	targets = ("/", "/hello", "/redirect1", "/redirect2", "/documentation", "/documentation2")	
	for url in targets:	
		aquests.get (server + url)
	aquests.get (server +"/members/", auth = ('admin', '1111'))
	aquests.post (server + "/post", {"username": "pytest"})	
	aquests.upload (server +"/upload", {"username": "pytest", "file1": jpg})	
	stub = aquests.rpc (server +"/rpc2/")
	stub.add_number (5, 7)
	if http2 and GRPC:
		stub = aquests.grpc (server +"/routeguide.RouteGuide/")
		point = route_guide_pb2.Point (latitude=409146138, longitude=-746188906)		
		stub.GetFeature (point)	

def make_stream_set (https = 0):
	server = (https and "https" or "http") + "://127.0.0.1:30371"
	aquests.get (server + "/documentation")
	aquests.get (server + "/documentation2")
	aquests.get (server + "/documentation3")
		
def test_app (launch):
	global ERRS
	ERRS = 0	
	with launch ("./examples/app.py") as engine:	
		aquests.configure (2, callback = assert_status, force_http1 = True)
		[ makeset (http2 = False) for i in range (2) ]
		aquests.fetchall ()
		assert ERRS < 4
		
		ERRS = 0
		aquests.configure (1, callback = assert_status)
		[ makeset (http2 = True) for i in range (2) ]
		aquests.fetchall ()		
		assert ERRS < 4
		
		ERRS = 0
		aquests.configure (1, callback = assert_status, http2_constreams = 2)
		[ makeset (http2 = True) for i in range (2) ]
		aquests.fetchall ()		
		assert ERRS < 4
		
		ERRS = 0	
		aquests.configure (1, callback = assert_status)
		[ make_stream_set () for i in range (4) ]
		aquests.fetchall ()		
		assert ERRS < 4

def test_https (launch):	
	global ERRS
		
	ERRS = 0
	with launch ("./examples/https.py", ssl = True) as engine:
		aquests.configure (2, callback = assert_status)
		[ makeset (1) for i in range (2) ]
		aquests.fetchall ()
		assert ERRS < 4
