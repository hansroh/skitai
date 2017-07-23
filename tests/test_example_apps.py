import confutil
from confutil import rprint, client

import pytest
import sys, os
import requests
import threading
import time
from requests.auth import HTTPDigestAuth
import xmlrpc.client
from examples.package import route_guide_pb2


def start_skitai (runner, script):
	runner.start ([sys.executable, os.path.join (confutil.getroot (), script)])
	time.sleep (3)
	
def assert_request (expect, url, *args, **karg):
	resp = requests.get ("http://127.0.0.1:5000" + url, *args, **karg)	
	assert resp.status_code == expect

def assert_post_request (expect, url, data, *args, **karg):
	resp = requests.post ("http://127.0.0.1:5000" + url, data, *args, **karg)	
	assert resp.status_code == expect

def assert_requests (expect, url, *args, **karg):
	resp = requests.get ("https://127.0.0.1:5000" + url, verify=False, *args, **karg)	
	assert resp.status_code == expect

def assert_post_requests (expect, url, data, *args, **karg):
	resp = requests.post ("https://127.0.0.1:5000" + url, data, verify=False, *args, **karg)	
	assert resp.status_code == expect

def test_auth (runner):
	start_skitai (runner, "app.py")
	try:
		assert_request (401, "/members/")
		assert_request (200, "/members/", auth = HTTPDigestAuth ("admin", "1111"))
	finally:		
		runner.kill ()
					
def test_app (runner):
	start_skitai (runner, "app.py")
	try:
		for url in (
				"/", "/documentation", "/documentation2", "/hello", "/redirect1", "/redirect2"				
			):
			assert_request (200, url)			
		assert_post_request (200, "/post", {"username": "pytest"})
		jpg = open (os.path.join (confutil.getroot (), "statics", "reindeer.jpg"), "rb")	
		assert_post_request (200, "/upload", {"username": "pytest"}, files = {"file1": jpg})
		
		with xmlrpc.client.ServerProxy("http://127.0.0.1:5000/rpc2/") as proxy:
			assert proxy.add_number (1, 3) == 4

	finally:		
		runner.kill ()

def test_app_single_thread (runner):
	start_skitai (runner, "app_single_thread.py")
	try:
		for url in ("/", "/documentation2", "/hello", "/redirect1", "/redirect2"):
			assert_request (200, url)			
		assert_request (508, "/documentation")
		assert_post_request (200, "/post", {"username": "pytest"})
		jpg = open (os.path.join (confutil.getroot (), "statics", "reindeer.jpg"), "rb")	
		assert_post_request (200, "/upload", {"username": "pytest"}, files = {"file1": jpg})
	finally:		
		runner.kill ()

#@pytest.mark.skip	
def test_https (runner):
	start_skitai (runner, "https.py")
	try:
		for url in ("/", "/documentation", "/documentation2", "/hello", "/redirect1", "/redirect2"):
			assert_requests (200, url)			
		assert_post_requests (200, "/post", {"username": "pytest"})
		jpg = open (os.path.join (confutil.getroot (), "statics", "reindeer.jpg"), "rb")	
		assert_post_requests (200, "/upload", {"username": "pytest"}, files = {"file1": jpg})
	finally:		
		runner.kill ()
		