from skitai.handlers import http2_handler
from skitai.handlers.http2 import vchannel, request, response
import pytest
from unittest.mock import Mock

def test_data_channel (channel):
	dc = vchannel.data_channel (1, channel, 1024)
	
	dc.current_request = Mock ()
	dc.current_request.rbytes = 0
	
	dc.set_data (b'pytest', 6)
	dc.set_data (b'pytest', 6)
	assert dc.get_chunk_size () == 6
	dc.set_data (b'pytest----', 10)	
	dc.set_data (b'pytest--', 8)	
	assert dc.get_chunk_size () == 0
	
	assert dc.get_data_size () == 30
	assert dc.get_content_length () == 1024
	assert len (dc.recv (12)) == 0
	
	