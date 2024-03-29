from rs4.misc import producers
from rs4.protocols.sock.impl.grpc.producers import grpc_producer
from rs4.protocols.sock.impl.http2.producers import h2frame_producer, h2header_producer
from confutil import rprint

def test_get_size ():
	pp = [grpc_producer, h2frame_producer, h2header_producer]
	for each in dir (producers):
		if not each.endswith ('_producer'):
			continue
		if each == 'globbing_producer':
			continue
		pp.append (getattr (producers, each))

	for p in pp:
		assert hasattr (p, 'get_size')
