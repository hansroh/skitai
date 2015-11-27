import asyncore, socket

class LazySocket (asyncore.dispatcher):
	address = ('127.9.9.9', 19999)
	def __init__ (self):
		asyncore.dispatcher.__init__ (self)
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind (self.address)
		self.listen (5)		
	
	def readable (self):
		return 1
	
	def writable (self):
		return 0
	
	def handle_accept (self):
		conn, addr = self.accept()
		conn.close ()
			
		
if __name__ == "__main__":
	s = LazyServer ()
	asyncore.DEBUG = 1
	asyncore.loop ()
	