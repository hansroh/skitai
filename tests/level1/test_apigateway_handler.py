import confutil
from skitai.server.handlers import vhost_handler
from skitai.server import offline
import skitai
import os
	
def test_apigateway_handler (wasc, app):
	vh = offline.install_vhost_handler (apigateway = 1, apigateway_authenticate = 0)
	
def test_apigateway_with_auth_handler (wasc, app):
	vh = offline.install_vhost_handler (apigateway = 1, apigateway_authenticate = 1)	
	
	
	