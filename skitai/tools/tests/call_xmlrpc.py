try:
	import xmlrpc.client as xmlrpclib
except ImportError:
	import xmlrpclib
	
s = xmlrpclib.Server ("http://127.0.0.1:5000/skitai")
print s.indians (10)

m = xmlrpclib.MultiCall (s)
m.indians (100)
m.indians (200)
m.indians (100)

r = m()
print tuple (r)


