import socket
import threading
import time 
import random
import urllib2
import socket as s
import sys

proxies = {'http': 'http://125.209.193.164:5001'}
	
d = {}
f = open ("d:/ttt/ll.txt")
for line in f:
	#if len (d) > 5: break
	line = line.lower ()
	x = line.find ("http://")
	if x == -1: continue
	y = line.find ("/", x + 7)
	if y == -1: continue
	host = line [x+7:y]
	if d.has_key (host): continue		
	d [host] = None

L = [
"sadb.skitai.com:5001/test/db",
"sadb.skitai.com:5001/test/dlb",
"sadb.skitai.com:5001/test/dmap",
"sadb.skitai.com:5001/test/lb",
"sadb.skitai.com:5001/test/map",
"sadb.skitai.com:5001/test/rpc",
#"sadb.skitai.com:5001/test/wget?url=http%3A//www.openfos.com/",
#"sadb.skitai.com:5001/openfos"
]

HOSTS = d.keys ()

for each in L:
	for i in range (200):
		HOSTS.append (each)

print len (HOSTS)		
LOCK = threading.Lock ()

#HOST = 'proxy.lufex.com'
HOST = '127.0.0.1'
PORT = 5000
	
def d (host):
	#print 'Connecting...', host
	if not host.startswith ("sadb.skitai.com"):
		proxy = urllib2.ProxyHandler(proxies)
		opener = urllib2.build_opener(proxy)
		req = urllib2.Request("http://%s" % host)
		f =	opener.open (req, timeout = 60)
	else:	
		f = urllib2.urlopen("http://%s" % host, timeout = 60)
	f.close ()
		
def d2 (host):
	print 'Connecting...', host
	f = urllib.urlopen("http://%s" % host, proxies=proxies)
	print 'Received', repr(data [:79])
			
def gets (func):
	global req, hits
	c = req
	while c:
		c -= 1
		host = random.choice (HOSTS)
		try:
			func (host)
			
		except Exception, why:
			LOCK.acquire ()
			try:
					print "ERROR >>>>%s, %s" % (host, why)
			finally:		
				LOCK.release ()
			
		else:
			hits += 1
			
			
def t ():		
	for i in range (clients):
		threading.Thread (target = gets, args = (d,)).start ()
		time.sleep (0.02)

def o ():
	host = random.choice (HOSTS)
	d (host)


clients = 300
req = 2000 - 1950
#req = 2000 - 1999

hits = 0
s = time.time ()
t ()
while threading.activeCount () > 1:
	#print "**********", hits
	time.sleep (1)

print "**********", hits
print time.time () - s

d ("www.bradfordcountypa.org/")

