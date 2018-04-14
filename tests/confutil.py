import os
from skitai.server.offline import server

def getroot ():
	return os.path.join (os.path.dirname (__file__), "examples")	
	
def rprint (*args):
	print ('* PYTEST DEBUG:', *args)

def assert_request (handler, request, expect_code):
	resp = server.handle_request (handler, request)
	assert resp.status_code == expect_code, rprint ("STATUS CODE:", resp.status_code)
	return resp
