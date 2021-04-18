from confutil import rprint, assert_request
import confutil
from skitai.handlers import vhost_handler
import skitai
import os
from skitai.testutil import offline as testutil

def test_proxypass_handler ():
	vh = testutil.install_vhost_handler ()


