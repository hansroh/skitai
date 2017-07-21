import confutil
from confutil import rprint, client
from mock import MagicMock
import pytest
from skitai.server.http_response import http_response
				
def test_http_response ():
	request = client.post ("http://www.skitai.com/", {"a": "b"})
	response = http_response (request)
