import pytest, os
from skitai.backbone.http_server import http_server, http_channel
from skitai.backbone.https_server import https_server, init_context

def test_http_server (log):
	s = http_server ('0.0.0.0', 3000, log.get ("server"), log.get ("request"))
	assert s.status ()['server_name']
	assert s.status ()['hash_id']
	s.close ()

def test_https_server (log):
	cert_dir = "./examples/resources/certifications"
	ctx = init_context (
		os.path.join (cert_dir, "server.crt"),
		os.path.join (cert_dir, "server.key"),
		"fatalbug"
	)
	s = https_server ('0.0.0.0', 3000, ctx, None, log.get ("server"), log.get ("request"))
	s.close ()

def test_http_channel (channel):
	conn = channel.socket
	conn.recv.return_value = b"GET /ping HTTP/1.1\r\nUser-Agent: pytest\r\n\r\n"
	content = b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"

	channel.use_sendlock ()
	channel.handle_read ()
	assert channel.request_counter.as_long () == 1
	assert channel.server.total_requests.as_long () == 1
	result = conn.getvalue ()
	assert result [:15] == b"HTTP/1.1 200 OK"
	channel.initiate_send ()
	channel.handle_write ()
	assert channel.bytes_out.as_long () == len (result)
	assert len (channel.producer_fifo) == 0
	assert channel.writable () == 0

	channel.journal ('A')
	channel.log ('B', 'pytest')

	assert channel.clean_shutdown_control (3, 10) == 0
	channel.handle_expt ()


