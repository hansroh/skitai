import confutil
from skitai.handlers import vhost_handler
from skitai.testutil import offline as testutil
import skitai
import os

def test_apigateway_handler (wasc, app):
	vh = testutil.install_vhost_handler (apigateway = 1, apigateway_authenticate = 0)

def test_apigateway_with_auth_handler (wasc, app):
	vh = testutil.install_vhost_handler (apigateway = 1, apigateway_authenticate = 1)


