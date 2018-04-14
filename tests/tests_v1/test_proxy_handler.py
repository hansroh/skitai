from confutil import rprint, assert_request
import confutil
import skitai
import os
from skitai.server.offline import server
	
def test_proxy_handler (wasc, app):
	ph = server.install_proxy_handler (wasc)
	