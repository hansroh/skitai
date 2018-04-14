import confutil
from skitai.server.handlers import vhost_handler
from skitai.server.offline import server
import skitai
import os
	
def test_apigateway_handler (wasc, app):
	vh = server.install_vhost_handler (wasc, apigateway = 1, apigateway_authenticate = 0)
	
def test_apigateway_with_auth_handler (wasc, app):
	vh = server.install_vhost_handler (wasc, apigateway = 1, apigateway_authenticate = 1)	
	
	
	