#!/usr/bin/env python

from . import http_server
from .counter import counter
import socket, time, asyncore
from M2Crypto import SSL
from skitai import lifetime

class https_channel (http_server.http_channel):
	def __init__(self, server, conn, addr):
		http_server.http_channel.__init__(self, server, conn, addr)
	
	def send(self, data):	
		result = self.socket._write_nbio(data)
		if result <= 0:
			return 0
		else:
			self.server.bytes_out.increment(result)
			return result	
		
	def recv(self, buffer_size):
		try:			
			result = self.socket._read_nbio(buffer_size)
			if result is None:
				return ''
				
			elif result == '':
				self.handle_close()
				return ''
				
			else:
				self.server.bytes_in.increment(len(result))
				return result
		
		except MemoryError:
			lifetime.shutdown (1, 1)
			
		except SSL.SSLError as why:
			if why [0] == "unexpected eof": # unexpected client's disconnection?
				self.handle_close()
				return ''			
			raise


class https_server (http_server.http_server):
	def handle_accept (self):
		self.total_clients.inc()
		
		try:
			conn, addr = self.accept()
		except socket.error:
			self.log_info ('server accept() threw an exception', 'warning')
			return
		except TypeError:
			self.log_info ('server accept() threw EWOULDBLOCK', 'warning')
			return		
		except:
			self.trace()
		
		try:
			ssl_conn=SSL.Connection(self.ssl_ctx, conn)
			ssl_conn._setup_ssl(addr)
			ssl_conn.accept_ssl ()
			https_channel (self, ssl_conn, addr)
			
		except SSL.SSLError as why:
			pass
		
		
def init_context(protocol, certfile, cafile, passphrase = None):
	ctx=SSL.Context(protocol)
	if not passphrase:
		ctx.load_cert(certfile)
	else:
		ctx.load_cert(certfile, callback = lambda x: passphrase)
	ctx.load_client_ca(cafile)
	ctx.load_verify_info(cafile)
	ctx.set_verify(SSL.verify_none, 10)
	ctx.set_allow_unknown_ca(1)
	ctx.set_session_id_ctx('https_srv')	
	return ctx
	
		
if __name__ == "__main__":
	import module_loader
	from .threads import threadlib
	import file_handler, xmlrpc_handler, soap_handler, cgi_handler, graph_handler, proxy_handler, logger
	
	pools = threadlib.request_queue()	
	daemons = {}
	for i in range (2):
		d=threadlib.request_thread (pools, 8)
		daemons [i+1]=d
		d.start()
	
	server_logger = framework.ServerLogger('%slog2/' % os.environ ['ALEPH_HOME'])
	modules = module_loader.ModuleLoader('%smod/' % os.environ ['ALEPH_HOME'], ['hello', 'iserver', 'system'], logger = server_logger)
	ctx = init_context('sslv3', 'cert/server.csr', 'cert/ca.crt', 'fatalbug')
	sv = https_server ('', 9443, ctx, https_channel, server_logger)
	
	class ServerComponent:
		queue = pools
		server = sv
		modules = modules
		channels = asyncore.socket_map
		daemons = daemons
	server=ServerComponent
	
	sh=soap_handler.soap_handler(server, 'http://infogent.sseki.com')
	sv.install_handler(sh)
	
	xh=xmlrpc_handler.xmlrpc_handler(server)
	sv.install_handler(xh)	
	
	ch=cgi_handler.cgi_handler(server)
	sv.install_handler(ch)
	
	gh=graph_handler.graph_handler()
	sv.install_handler(gh)
	
	ph=proxy_handler.proxy_handler(server)
	sv.install_handler(ph)
	
	fh=file_handler.file_handler('/home/infogent/infogent/doc/')
	sv.install_handler(fh)
	
	if os.name == 'posix': usepoll = 1
	else: usepoll = 0	
	
	Rand.load_file('randpool.dat', -1)	
	try: 
		asyncore.loop(30.0, usepoll)		
	except: 
		server_logger.trace()		
	Rand.save_file('randpool.dat')
	os.abort ()
	