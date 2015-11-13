import jsonrpclib as x

s=x.Server("http://admin:whddlgkr@localhost:3426/json")

#print s.admin.test2([1,2])

m=x.MultiCall(s)
m.admin()
m.admin.test1([1,2,3],3)
m.admin.test2([4,5])

tt = m().results
print tt
print type (tt)
	


