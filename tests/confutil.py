import os
from skitai.testutil.offline import server
try:
	from examples.services import route_guide_pb2
except ImportError:
	from examples.services import route_guide_pb2_v3 as route_guide_pb2

def getroot ():
	return os.path.join (os.path.dirname (__file__), "examples")

def rprint (*args):
	print ('* PYTEST DEBUG:', *args)

