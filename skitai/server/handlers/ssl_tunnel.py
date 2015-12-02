from skitai.server.threads import trigger


class ClientToServer:
	collector = None
	producer = None
	def __init__ (self, asyncon):
		self.asyncon = asyncon
		self.bytes = 0
		
	def collect_incoming_data (self, data):
		self.bytes += len (data)
		self.asyncon.push (data)
	
	def abort (self):
		self.close ()
			
	def close (self):
		self.asyncon.close_socket ()

		
class ServerToClient:
	def __init__ (self, channel, asyncon):
		self.channel = channel
		self.asyncon = asyncon
		
		self.bytes = 0				
		self.asyncon.set_terminator (None)
		self.channel.set_terminator (None)						
		self.cli2srv = ClientToServer (self.asyncon)
		self.channel.current_request = self.cli2srv
	
	def collect_incoming_data (self, data):
		self.bytes += len (data)		
		self.channel.push (data)
	
	def retry (self):
		return False
	
	def log (self):
		self.channel.server.log_request (
			'%s:%d CONNECT tunnel://%s:%d HTTP/1.1 200 %d/%d'
			% (self.channel.addr[0],
			self.channel.addr[1],			
			self.asyncon.address [0],
			self.asyncon.address [1],
			self.cli2srv.bytes,
			self.bytes)
			)
	
	def done (self, *args, **kargs):
		self.abort ()
				
	def abort (self):
		self.log ()
		#self.cli2srv.close ()
		self.channel.close ()
		
