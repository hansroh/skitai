import xmlrpclib as x

s=x.Server("http://admin:whddlgkr@localhost:3426/rpc2")

#print s.admin.test2([4,5], 1)

m=x.MultiCall(s)
m.admin()
m.admin.test1([1,2,3],1)
m.admin.test2([4,5])

print m().results
	


