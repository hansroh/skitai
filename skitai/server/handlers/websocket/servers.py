import threading
from . import specs

class WebSocketServers:
	def __init__ (self):
		self.lock = threading.RLock ()
		self.wss = {}
	
	def get (self, gid):
		self.lock.acquire ()
		wss = self.wss [gid]
		self.lock.release ()
		return wss
		
	def has_key (self, gid):	
		self.lock.acquire ()
		has = gid in self.wss
		self.lock.release ()
		return has
		
	def create (self, gid):	
		self.lock.acquire ()
		wss = WebSocketServer (gid)
		self.wss [gid] = wss
		self.lock.release ()
		return wss
	
	def remove (self, gid):
		self.lock.acquire ()
		try: 
			del self.wss [gid]			
		except KeyError: 
			pass	
		self.lock.release ()		
	
	def close (self):
		self.lock.acquire ()
		for s in list (self.wss.values ()):
			s.close ()
		self.lock.release ()

		
class WebSocketServer (specs.WebSocket2):
	def __init__ (self, gid):
		self._closed = False
		self.gid = gid
		self.lock = threading.RLock ()
		self.cv = threading.Condition ()
		self.messages = []
		self.clients = {}
		
	def add_client (self, ws):
		self.lock.acquire ()
		self.clients [ws.client_id] = ws
		self.lock.release ()
		self.handle_message (ws.client_id, 1)
	
	def handle_close (self, client_id):
		self.lock.acquire ()
		try: del self.clients [client_id]
		except KeyError: pass		
		self.lock.release ()
		self.handle_message (client_id, -1)
		
	def handle_message (self, client_id, msg):
		self.cv.acquire()
		self.messages.append ((client_id, msg))
		self.cv.notifyAll ()
		self.cv.release ()
			
	def close (self):
		websocket_servers.remove (self.gid)
		self.clients = {}
		self.cv.acquire()
		self._closed = True
		self.cv.notifyAll ()
		self.cv.release ()
		
	def send (self, *args, **karg):
		raise AssertionError ("Can't use send() on WEBSOCKET_MULTICAST spec, use send_to(client_id, msg, op_code)")
	
	def sendto (self, client_id, msg, op_code = specs.OPCODE_TEXT):		
		self.lock.acquire ()
		try:
			client = self.clients [client_id]
		except KeyError:
			client = None	
		self.lock.release ()
		if client:
			client.send (msg, op_code)
		
	def sendall (self, msg, op_code = specs.OPCODE_TEXT):
		self.lock.acquire ()
		clients = list (self.clients.keys ())
		self.lock.release ()
		for client_id in clients:
			self.sendto (client_id, msg)


websocket_servers = WebSocketServers ()

	