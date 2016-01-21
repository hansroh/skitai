from skitai.protocol.http import response

class Response (response.Response):
	def __init__ (self, code, msg, opcode, data = None):
		self.code = code
		self.msg = msg
		self.data = data
		self.version = "1.1"
		self.header = ["OPCODE: %s" % opcode]
	
	def get_content (self):
		return self.data
	
	def done (self):
		pass
	