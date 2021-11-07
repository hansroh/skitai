from rs4.misc import producers
from skitai.protocols.sock.impl.grpc.producers import grpc_producer
from skitai.protocols.sock.impl.http2.producers import h2frame_producer, h2header_producer
from skitai.handlers.proxy.response import ProxyResponse
from confutil import rprint

def test_get_size ():
	pp = [grpc_producer, h2frame_producer, h2header_producer, ProxyResponse]
	for each in dir (producers):
		if not each.endswith ('_producer'):
			continue
		if each == 'globbing_producer':
			continue
		pp.append (getattr (producers, each))

	for p in pp:
		assert hasattr (p, 'get_size')
