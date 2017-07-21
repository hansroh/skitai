from confutil import client, rprint, assert_request
import confutil
from skitai.server.handlers import vhost_handler
import skitai
import os
	
def test_proxy_handler (wasc, app):
	ph = confutil.install_proxy_handler (wasc)
	