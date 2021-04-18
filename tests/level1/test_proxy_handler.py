from confutil import rprint, assert_request
import confutil
import skitai
import os
from skitai.testutil import offline as testutil

def test_proxy_handler ():
	ph = testutil.install_proxy_handler ()
