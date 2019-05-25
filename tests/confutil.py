import os
from skitai.testutil import server
from skitai.testutil import server, client as cli 
from examples.services import route_guide_pb2

client = cli.Client ()

def getroot ():
	return os.path.join (os.path.dirname (__file__), "examples")	
	
def rprint (*args):
	print ('* PYTEST DEBUG:', *args)

def assert_request (handler, request, expect_code):
	resp = client.handle_request (request, handler)
	assert resp.status_code == expect_code, rprint ("STATUS CODE:", resp.status_code)
	return resp
