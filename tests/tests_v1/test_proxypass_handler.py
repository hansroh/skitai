from confutil import client, rprint, assert_request
import confutil
from skitai.server.handlers import vhost_handler
import skitai
import os
	
def test_proxypass_handler (wasc, app):
	vh = confutil.install_vhost_handler (wasc)
	

