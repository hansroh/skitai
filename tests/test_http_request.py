from aquests.protocols.http import http_util
from confutil import client

def test_request ():	
	request = client.get ("/")
	