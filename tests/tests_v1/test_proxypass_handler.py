from confutil import rprint, assert_request
import confutil
from skitai.server.handlers import vhost_handler
import skitai
import os
from skitai.server import offline
	
def test_proxypass_handler ():
	vh = offline.install_vhost_handler ()
	

