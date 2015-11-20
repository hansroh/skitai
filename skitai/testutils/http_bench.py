#! /usr/local/bin/python1.4
# -*- Mode: Python -*-

import threading
import asyncore
import socket
import string
import sys
import random
import time
import urllib.request, urllib.error, urllib.parse
from asyncore import socket_map, poll
	

class timer:
		def __init__ (self):
				self.start = time.time()
		def end (self):
				return time.time() - self.start


def maintern ():
	for fd, obj in list(socket_map.items ()):
		if time.time () - obj.event_time > 20:
			obj.handle_close ()
			#blurt ('d')
	
	
MAX = 0
LAST_MAINTERN = time.time ()
def loop (timeout=30.0):
		global MAX, LAST_MAINTERN
		
		while socket_map:
				if len(socket_map) > MAX:
						MAX = len(socket_map)
				poll (timeout)
				if time.time () - LAST_MAINTERN > 10:
					maintern ()
					LAST_MAINTERN = time.time ()
					

def blurt (thing):
		sys.stdout.write (thing)
		sys.stdout.flush ()

total_sessions = 0
total_errors = 0
resp_codes = {}
class http_client (asyncore.dispatcher_with_send):
	def __init__ (self, host, port, uri='/', num=10):
		asyncore.dispatcher_with_send.__init__ (self)
		self.create_socket (socket.AF_INET, socket.SOCK_STREAM)
		self.host = host
		self.port = port
		self.uri = uri
		if self.uri [0] != "/":
			self.uri = "http://" + self.uri
		self.num = num
		self.bytes = 0
		self.connect ((host, port))
		self.event_time = 0
		self.data = None

	def log (self, *info):
		pass
	
	def handle_error(self):
		self.handle_close ()
		
	def handle_connect (self):
		self.event_time = time.time ()
		self.connected = 1				
		#blurt ('o')
		
		b = [
		"GET %s HTTP/1.%d" % (self.uri, random.randrange (1)),
		"Host: %s:%d" % (self.host, self.port),
		"Accept-Encoding: gzip, deflate",
		"Connection: close",
		"Cache-Control: max-age=0"
		]
		self.send ("\r\n".join (b) + "\r\n\r\n")
		
	def handle_read (self):
		self.event_time = time.time ()
		blurt ('.')
		d = self.recv (8192)
		self.bytes = self.bytes + len(d)
		if not self.data:
			self.data = d

	def handle_close (self):
		global total_sessions, total_errors, resp_codes
		total_sessions = total_sessions + 1
		if self.bytes == 0:
			total_errors += 1			
		blurt ('(%d)' % total_sessions)	
		#blurt ('(%d)' % (self.bytes))
		self.close()
		if self.data:
			code = self.data [9:12]
			#blurt ('[%s]' % (code))
		else:
			code = "900"
			
		try: resp_codes [code] += 1
		except KeyError: resp_codes [code] = 1	
		
		if self.num:
			http_client (self.host, self.port, random.choice (HOSTS), self.num-1)
						

HOSTS = []
def make_testset (testproxy):
	global HOSTS
	
	if testproxy:
		PTEST = {}
		try:
			f = open ("hosts.txt")
		except (IOError, OSError):
			print("[error] no hosts.txt file, ignore proxy test")
		else:	
			for line in f:			
				host = line.lower ().strip ()
				PTEST [host] = None
			HOSTS = list(PTEST.keys ())
	
	L = [
			"/test/db",
			"/test/dlb",
			"/test/dmap",
			"/test/lb",
			"/test/lb2",
			"/test/lb3",
			"/test/map",
			"/test/map2",
			"/test/map3",
			"/images/concept.png",
			"/test/rpc",
			"/test/wget",
			"/reverseproxy",
			"/test/options",
			"/test/upload"
	]	
	
	for each in L:
		for i in range (770):
			HOSTS.append (each)
	
	print(len (HOSTS))
	

LOCK = threading.Lock ()
def use_urllib (host):
	#print 'Connecting...', host
	if host[0] != "/":
		proxy = urllib.request.ProxyHandler(PROXIES)
		opener = urllib.request.build_opener(proxy)
		req = urllib.request.Request("http://%s" % host)
		f =	opener.open (req, timeout = 20)
	else:	
		f = urllib.request.urlopen("http://%s:%d%s" % (HOST, PORT, host), timeout = 20)
	f.close ()
		
def gets (func):
	global req, total_sessions, resp_codes, total_errors
	c = req
	while c:
		c -= 1
		host = random.choice (HOSTS)
		total_sessions += 1
		try:
			func (host)
			
		except Exception as why:
			LOCK.acquire ()
			try:
				code = why.getcode ()
			except:
				total_errors += 1
				code = 900
			finally:								
				LOCK.release ()
		else:
			code = 200
		
		LOCK.acquire ()		
		blurt (".(%d)" % total_sessions)
		try: resp_codes [code] += 1
		except KeyError: resp_codes [code] = 1	
		LOCK.release ()
					
def runthread ():	
	global MAX	
	for i in range (clients):
		MAX += 1
		threading.Thread (target = gets, args = (use_urllib,)).start ()
		time.sleep (0.02)


def usage ():
	print("%s [options]" % sys.argv[0])
	print("""
	--help
	-c num client
	-r num request per client
	-h sadb, default is ibiz
	-p enable proxy test
	-t threading mode, default is async mode
	""")
	
	
if __name__ == '__main__':
	import getopt
	
	argopt = getopt.getopt(sys.argv[1:], "c:r:h:pt", ["help"])
	clients = 20
	req = 5
	testproxy = False
	host = "ibizcast"
	async = True
	
	for k, v in argopt [0]:
		if k == "-c": 
			clients = int (v)
		elif k == "-r":	
			req = int (v)
		elif k == "-h":
			host = v
		elif k == "-p":	
			testproxy = True
		elif k == "-t":	
			async = False
		elif k == "--help":		
			usage ()
			sys.exit ()
	 
	if host == "sadb":		
		HOST = 'sadb.skitai.com'
		PORT = 5001		
	else:		
		HOST = 'ibizcast.skitai.com'
		PORT = 5000
	
	PROXIES = {'http': "http://%s:%d" % (HOST, PORT)}
	make_testset (testproxy)	
	
	t = timer()
	if async:
		list(map (lambda x: http_client (HOST, PORT, random.choice (HOSTS), req-1), list(range(clients))))
		loop()
	else:		
		runthread ()
		while threading.activeCount () > 1:
			time.sleep (1)
	
	total_time = t.end()
	
	print((
					'\n%d clients\n%d hits/client\n'
					'total hits:%d\n'
					'total errors:%d\n%.3f seconds\ntotal hits/sec:%.3f' % (
									clients,
									req,
									total_sessions,
									total_errors,
									total_time,
									total_sessions / total_time
									)
					))
					
	print('Max. number of concurrent sessions: %d' % (MAX))
	codes = list(resp_codes.items ())
	codes.sort ()
	
	print("HTTP Response Code Stats")
	for k, v in codes:
		print("  %s: %d" % (k, v))

# linux 2.x, talking to medusa
# 50 clients
# 1000 hits/client
# total_hits:50000
# 2255.858 seconds
# total hits/sec:22.165
# Max. number of concurrent sessions: 50
