from aquests.lib import producers
from aquests.protocols.grpc.producers import grpc_producer
from aquests.protocols.http2.producers import h2frame_producer, h2header_producer
from skitai.server.handlers.proxy.response import ProxyResponse
from confutil import rprint 

def test_get_size ():
	pp = [grpc_producer, h2frame_producer, h2header_producer, ProxyResponse]
	for each in dir (producers):
		if not each.endswith ('_producer'):
			continue
		pp.append (getattr (producers, each))	
	
	for p in pp:					
		assert hasattr (p, 'get_size')
		