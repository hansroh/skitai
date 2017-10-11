import time

class AsynTunnel:
	collector = None
	producer = None
	def __init__ (self, asyncon, handler):
		self.asyncon = asyncon
		self.handler = handler
		self.bytes = 0
		self.asyncon.set_terminator (None)
		
	def collect_incoming_data (self, data):		
		self.bytes += len (data)		
		self.asyncon.push (data)
	
	def close (self):
		# closed by channel		
		self.handler.channel_closed ()
		
	
class TunnelHandler:
	
	def __init__ (self, asyncon, request, channel):		
		self.asyncon = asyncon		
		self.request = request
		self.channel = channel
		
		self.asyntunnel = AsynTunnel (asyncon, self)		
		self.channel.die_with (self.asyntunnel, "tunnel")
		
		self.bytes = 0
		self.stime = time.time ()
				
	def trace (self, name = None):
		if name is None:
			name = "tunnel://%s:%d" % self.asyncon.address
		self.channel.trace (name)
		
	def log (self, message, type = "info"):
		uri = "tunnel://%s:%d" % self.asyncon.address
		self.channel.log ("%s - %s" % (uri, message), type)
					
	def collect_incoming_data (self, data):		
		self.bytes += len (data)
		self.channel.push (data)
		
	def log_request (self):
		htime = (time.time () - self.stime) * 1000
		self.channel.server.log_request (
			'%s:%d %s CONNECT %s:%d HTTP/1.1 200 %d %d - - %s %s %s %dms %dms'
			% (self.channel.addr[0],
			self.channel.addr[1],			
			self.request.host,
			self.asyncon.address [0],
			self.asyncon.address [1],
			self.asyntunnel is not None and self.asyntunnel.bytes or 0,
			self.bytes,
			self.request.user and '"' + self.request.user.name + '"' or "-",
			self.request.token and self.request.token or "-",			
			self.request.user_agent and '"' + self.request.user_agent + '"' or "-",
			htime,
			htime
			)
		)
		
	def connection_closed (self, why, msg):	
		# another word, asyncon closed	
		if self.channel:
			self.channel.handle_abort ()
			self.channel.current_request = None
		
	def channel_closed (self):
		self.asyncon.handle_abort ()
		