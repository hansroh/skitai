from confutil import rprint, assert_request
import confutil
from skitai.server.handlers import vhost_handler
import skitai
import os
from skitai.server.offline import server
	
def test_proxypass_handler (wasc, app):
	vh = server.install_vhost_handler (wasc)
	

