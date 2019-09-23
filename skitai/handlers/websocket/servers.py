import threading
from . import specs
try: from urllib.parse import quote_plus
except ImportError: from urllib import quote_plus
import skitai

class WebSocketServers:
	def __init__ (self, wasc):
		self.wasc = wasc
		self._nomore = False
		self.lock = threading.RLock ()
		self.wss = {}

	def get (self, gid, default = None):
		with self.lock:
			return self.wss.get (gid, default)

	def has_key (self, gid):
		with self.lock:
			has = gid in self.wss
		return has

	def create (self, gid, *args):
		with self.lock:
			if self._nomore:
				return

		wss = WebSocketServer (gid, *args)
		with self.lock:
			self.wss [gid] = wss
		return wss

	def remove (self, gid):
		with self.lock:
			try:
				del self.wss [gid]
			except KeyError:
				pass

	def close (self):
		with self.lock:
			wss = list (self.wss.items ())
			self._nomore = True
		for k, s in wss:
			self.wasc.logger ('server', '...closing websockket %s' % k)
			s.close ()

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
		self.client_id = None

	def add_client (self, ws):
		self.clients [ws.client_id] = ws
		ws.handle_message (1, skitai.WS_EVT_OPEN)

	def handle_client (self, client_id, event):
		if event == skitai.WS_EVT_CLOSE: # exit
			try: del self.clients [client_id]
			except KeyError: pass
			if not self.clients:
				return self.close ()

	def close (self):
		websocket_servers.remove (self.gid)
		self.clients = {}
		self._closed = True

	def send (self, msg, client_id = None, op_code = -1):
		msg, op_code = self.build_data (msg, op_code)
		if client_id:
			self.__sendto (client_id, msg, op_code)
		else:
			self.__sendall (msg, op_code)

	def __sendall (self, msg, op_code = -1):
		clients = list (self.clients.keys ())
		for client_id in clients:
			self.__sendto (client_id, msg, op_code)

	def __sendto (self, client_id, msg, op_code = -1):
		try:
			client = self.clients [client_id]
		except KeyError:
			client = None
		if client:
			client.send (msg, op_code)

websocket_servers = None

def start_websocket (wasc):
	global websocket_servers

	websocket_servers = WebSocketServers (wasc)


