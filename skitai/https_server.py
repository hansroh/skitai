#!/usr/bin/env python

from . import http_server
from .counter import counter
import socket, time, asyncore
import ssl
from skitai import lifetime
import os, sys, errno
import skitai
from errno import EWOULDBLOCK
from aquests.protocols.http2 import H2_PROTOCOLS
			
class https_channel (http_server.http_channel):
	ac_out_buffer_size = 65536
	ac_in_buffer_size = 65536
	
	def __init__(self, server, conn, addr):
		http_server.http_channel.__init__(self, server, conn, addr)
		
	def send(self, data):	
		#print	("SEND", str (data), self.get_terminator ())
		try:
			result = self.socket.send(data)	
				
		except ssl.SSLError as why:
			if why.errno == ssl.SSL_ERROR_WANT_WRITE:
				return 0
			elif why.errno == ssl.SSL_ERROR_ZERO_RETURN:				
				self.handle_close ()
				return 0
			else:
				raise
					
		if result <= 0:
			return 0
		else:
			self.server.bytes_out.increment(result)
			return result	
		
	def recv(self, buffer_size = 65535):
		try:			
			result = self.socket.recv(buffer_size)
			#print ("~~~~~~~~~~~~~", len (result), result)
			if result is None:
				return b''
				
			elif result == b'':
				self.handle_close()
				return b''
				
			else:
				self.server.bytes_in.increment(len(result))
				return result
		
		except MemoryError:
			lifetime.shutdown (1, 1.0)
		
		except ssl.SSLError as why:			
			if why.errno == ssl.SSL_ERROR_WANT_READ:				
				try: 
					raise BlockingIOError				
				except NameError:
					raise socket.error (EWOULDBLOCK)		
			# closed connection
			elif why.errno in (ssl.SSL_ERROR_ZERO_RETURN, ssl.SSL_ERROR_EOF):
				self.handle_close ()
				return b''
			else:
				raise
					

class https_server (http_server.http_server):
	def __init__ (self, ip, port, ctx, server_logger = None, request_logger = None):
		http_server.http_server.__init__ (self, ip, port, server_logger, request_logger)
		self.ctx = ctx
		self.socket = self.ctx.wrap_socket (self.socket, server_side = True)
		
	def handle_accept (self):
		self.total_clients.inc()
		
		try:
			conn, addr = self.accept()
		except socket.error:
			#self.log_info ('server accept() threw an exception', 'warning')
			return
		except TypeError:
			if os.name == "nt":
				self.log_info ('server accept() threw EWOULDBLOCK', 'warning')
			return		
		except:
			self.trace()
		
		https_channel (self, conn, addr)
		
	
def init_context (certfile, keyfile, pass_phrase):	
	try:
		protocol = ssl.PROTOCOL_TLS
	except AttributeError:
		protocol = ssl.PROTOCOL_SSLv23			
	ctx = ssl.SSLContext (protocol)
	try:	
		ctx.set_alpn_protocols (H2_PROTOCOLS)
	except AttributeError:		
		ctx.set_npn_protocols (H2_PROTOCOLS)
	ctx.load_cert_chain (certfile, keyfile, pass_phrase)
	ctx.check_hostname = False
	return ctx
	
		
if __name__ == "__main__":
	import module_loader
	from aquests.athreads import threadlib
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
	