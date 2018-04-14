from confutil import rprint, assert_request
import confutil
import skitai
import os
from skitai.server import offline
	
def test_proxy_handler ():
	ph = offline.install_proxy_handler ()
	