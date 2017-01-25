import threading
from . import specs
try: from urllib.parse import quote_plus
except ImportError: from urllib import quote_plus	
import skitai
from skitai.saddle import part

class WebSocketServers:
	def __init__ (self, wasc):
		self.wasc = wasc
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
		
	def create (self, gid, *args):	
		self.lock.acquire ()
		wss = WebSocketServer (gid, *args)
		self.wss [gid] = wss
		self.lock.release ()
		return wss
	
	def create_threaded (self, gid, *args):	
		self.lock.acquire ()
		wss = ThreadedWebSocketServer (gid, *args)
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
		for k, s in list (self.wss.items ()):
			self.wasc.logger ('server', '...closing websockket %s' % k)
			s.close ()
		self.lock.release ()
	
	def cleanup (self):
		self.close ()
		

class WebSocketServer (specs.WebSocket1):
	def __init__ (self, gid, handler, request, apph, env, message_encoding = None):
		specs.WebSocket.__init__ (self, handler, request, message_encoding)
		self._closed = False
		self.gid = gid
		self.apph = apph
		self.env = env
		self.messages = []
		self.clients = {}		
			
	def add_client (self, ws):
		self.clients [ws.client_id] = ws
		ws.handle_message (1, skitai.WS_EVT_ENTER)
	
	def handle_message (self, client_id, msg, querystring, params, message_param):		
		if msg == -1: # exit
			try: del self.clients [client_id]
			except KeyError: pass
			msg = ""			
			if not self.clients:
				return self.close ()
		elif msg == 1: # enter
			msg = ""
			
		self.env ["QUERY_STRING"] = querystring + quote_plus (msg)			
		self.env ["websocket.params"] = params
		self.env ["websocket.params"][message_param] = self.message_decode (msg)		
		args = (self.request, self.apph, (self.env, self.start_response), self.wasc.logger)
		if self.env ["wsgi.multithread"]:
			self.wasc.queue.put (specs.PooledJob (*args))
		else:
			specs.PooledJob (*args) ()
		
	def close (self):
		websocket_servers.remove (self.gid)
		self.clients = {}
		self._closed = True
		
	def send (self, msg, op_code = -1):
		if type (msg) is tuple:
			try: msg, client, op_code = msg
			except ValueError: msg, client = msg
		else:
			client = None		
		
		if op_code == -1:
			op_code = self.default_op_code		
		msg = self.message_encode (msg)
		
		if client:
			self.sendto (client, msg, op_code)
		else:
			self.sendall (msg, op_code)
			
	def sendto (self, client_id, msg, op_code = -1):		
		try:
			client = self.clients [client_id]
		except KeyError:
			client = None	
		if client:
			client.send (msg, op_code)
		
	def sendall (self, msg, op_code = -1):
		clients = list (self.clients.keys ())
		for client_id in clients:
			self.sendto (client_id, msg)

websocket_servers = None

def start_websocket (wasc):
	global websocket_servers
	
	websocket_servers = WebSocketServers (wasc)
	
	
