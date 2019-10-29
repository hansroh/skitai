import confutil
from confutil import rprint
import pytest
from skitai.backbone.http_response import http_response, UNCOMPRESS_MAX, ONETIME_COMPRESS_MAX
from rs4 import producers
import os
from aquests.protocols.http2.producers import h2frame_producer, h2header_producer
import threading
from h2.connection import H2Connection
from skitai.testutil import server
from skitai.handlers.http2.response import response as http2_response
from unittest.mock import MagicMock

def make_response (client, compression = "defalte, gzip", version = "1.1"):
	request = client.get (
        "http://www.skitai.com/",
        headers = [("Accept-Encoding", compression)],
        version = version
    )

	if request.version == "2.0":
		request.http2 = MagicMock ()
		request.stream_id = 1
		return http2_response (request)
	return http_response (request)

def payload (length = 1024):
	return b"A" * length

def test_http_response (client):
	request = client.get ("http://www.skitai.com/")
	response = http_response (request)

def test_makers (client):
	# BASIC ARGS TEST
	response = make_response (client, 'none', "2.0")
	assert response.request.get_header ('accept-encoding') == "none"
	assert response.request.version == "2.0"

def test_http1 (client):
	# # HTTP/1.0 NO CHUNK
	response = make_response (client, version = "1.0")
	response ("200 OK", "", headers = [("Content-Type", "text/plain")])
	response.push_and_done (payload (UNCOMPRESS_MAX + 1))
	assert response.get ("content-encoding") == "gzip"
	assert response.get ("transfer-encoding") is None

	response = make_response (client, version = "1.0")
	response ("200 OK", "", headers = [("Content-Type", "text/plain")])
	response.push_and_done (payload (ONETIME_COMPRESS_MAX + 1))
	assert response.get ("content-encoding") is None
	assert response.get ("transfer-encoding") is None

	response = make_response (client, version = "1.0")
	response ("200 OK", "", headers = [("Content-Type", "appication/pdf")])
	response.push_and_done (payload (UNCOMPRESS_MAX + 1))
	assert response.get ("content-encoding") is None
	assert response.get ("transfer-encoding") is None

def test_http1_1 (client):
	# HTTP/1.1
	response = make_response (client)
	response ("200 OK", "", headers = [("Content-Type", "text/plain")])
	response.push_and_done (payload (UNCOMPRESS_MAX - 1))
	assert response.get ("content-encoding") is None
	assert response.get ("transfer-encoding") == "chunked"

	response = make_response (client)
	response ("200 OK", "", headers = [("Content-Type", "text/plain")])
	response.push_and_done (payload (UNCOMPRESS_MAX + 1))
	assert response.get ("content-encoding") == "gzip"
	assert response.get ("transfer-encoding") == "chunked"

	response = make_response (client)
	response ("200 OK", "", headers = [("Content-Type", "appication/pdf")])
	response.push_and_done (payload (UNCOMPRESS_MAX + 1))
	assert response.get ("content-encoding") is None
	assert response.get ("transfer-encoding") == "chunked"

	response = make_response (client, version = "1.1")
	response ("200 OK", "", headers = [("Content-Type", "text/plain")])
	response.push_and_done (payload (ONETIME_COMPRESS_MAX + 1))
	assert response.get ("content-encoding") == "gzip"
	assert response.get ("transfer-encoding") == "chunked"

def test_http2 (client):
	# HTTP/2.0
	response = make_response (client, version = "2.0")
	response ("200 OK", "", headers = [("Content-Type", "application/pdf")])
	response.push_and_done (payload (ONETIME_COMPRESS_MAX + 1))
	assert response.get ("content-encoding") is None
	assert response.get ("transfer-encoding") is None

	response = make_response (client, version = "2.0")
	response ("200 OK", "", headers = [("Content-Type", "text/plain")])
	response.push_and_done (payload (ONETIME_COMPRESS_MAX + 1))
	assert response.get ("content-encoding") == "gzip"
	assert response.get ("transfer-encoding") is None

	response = make_response (client, version = "2.0")
	response ("200 OK", "", headers = [("Content-Type", "text/plain")])
	response.push_and_done (payload (UNCOMPRESS_MAX - 1))
	assert response.get ("content-encoding") is None
	assert response.get ("transfer-encoding") is None

def test_producers (client):
	def g ():
		for i in range (10):
			yield ("A" * 10).encode ("utf8")

	def l ():
		return ([("A" * 10).encode ("utf8")] * 10)

	class s:
		def __init__ (self):
			self.d = list (range (10))
			self.closed = 0

		def close (self):
			self.closed = 1

		def read (self, size):
			if not self.d:
				return b""
			self.d.pop ()
			return ("A" * size).encode ("utf8")

	response = make_response (client)
	jpg = open (os.path.join (confutil.getroot (), "statics", "reindeer.jpg"), "rb")
	response ("200 OK", "", headers = [("Content-Type", "application/octet-stream")])
	response.push_and_done (producers.file_producer (jpg))
	assert response.get ("content-encoding") is None
	assert response.get ("transfer-encoding") == "chunked"
	assert jpg.closed

	response = make_response (client)
	response ("200 OK", "", headers = [("Content-Type", "text/html")])
	response.push_and_done (producers.iter_producer (g ()))
	assert response.get ("content-encoding") == "gzip"
	assert response.get ("transfer-encoding") == "chunked"

	response = make_response (client)
	response ("200 OK", "", headers = [("Content-Type", "text/html")])
	response.push_and_done (producers.list_producer (l ()))
	assert response.get ("content-encoding") is None
	assert response.get ("transfer-encoding") == "chunked"

	response = make_response (client)
	response ("200 OK", "", headers = [("Content-Type", "text/html")])
	producer = s ()
	response.push_and_done (producers.closing_stream_producer (producer))
	assert response.get ("content-encoding") == "gzip"
	assert response.get ("transfer-encoding") == "chunked"
	assert producer.closed

	response = make_response (client)
	response ("200 OK", "", headers = [("Content-Type", "text/html")])
	jpg = open (os.path.join (confutil.getroot (), "statics", "reindeer.jpg"), "rb")
	response.push (producers.closing_stream_producer (s ()))
	response.push (producers.list_producer (l ()))
	response.push (producers.iter_producer (g ()))
	response.push (producers.file_producer (jpg))
	response.done ()

	assert response.get ("content-encoding") == "gzip"
	assert response.get ("transfer-encoding") == "chunked"
	assert producer.closed
	assert jpg.closed

	response = make_response (client)
	response ("200 OK", "", headers = [("Content-Type", "text/html")])
	jpg = open (os.path.join (confutil.getroot (), "statics", "reindeer.jpg"), "rb")
	response.push (producers.closing_stream_producer (s ()))
	response.push (producers.list_producer (l ()))
	response.push (producers.iter_producer (g ()))
	response.push (producers.file_producer (jpg))
	response.done ()

	response = make_response (client, version = "2.0")
	response ("200 OK", "", headers = [("Content-Type", "text/html")])
	jpg = open (os.path.join (confutil.getroot (), "statics", "reindeer.jpg"), "rb")
	conn = MagicMock ()
	conn.data_to_send.return_value = jpg.read ()
	p = h2frame_producer (
		1, 0, 1, producers.file_producer (jpg), conn, threading.Lock ()
	)
	response.push_and_done (p)
	assert response.get ("content-encoding") is None
	rprint (response.reply_headers)
	assert response.get ("transfer-encoding") is None
