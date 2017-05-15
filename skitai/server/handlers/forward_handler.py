from .. import https_server

class Handler:
	def __init__ (self, wasc, forward_to = 443):
		self.wasc = wasc
		self.forward_to = forward_to
		
	def match (self, request):
		if not isinstance (request.channel, https_server.https_channel):
			return 1
	
	def handle_request (self, request):
		location = "https://%s%s%s" % (
			request.get_header ("host").split (":") [0], 
			self.forward_to != 443 and (":%d" % self.forward_to) or "",
			request.uri
		)
		request.response ["Location"] = location
		request.response.error (301)
