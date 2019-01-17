from confutil import rprint, assert_request
import confutil
import skitai
import os
from skitai import offline
	
def test_proxy_handler ():
	ph = offline.install_proxy_handler ()
	