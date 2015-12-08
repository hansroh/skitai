#http://assets.bwbx.io/business/public/javascripts/application.07fa923a.js HTTP/1.1  200 303523
import socket
import time

req = """
GET /stock/comm/btn_more.gif HTTP/1.0
Host: image.moneta.co.kr
User-Agent: Mozilla/5.0 (Windows NT 6.1; rv:38.0) Gecko/20100101 Firefox/38.0
Accept: image/png,image/*;q=0.8,*/*;q=0.5
Accept-Language: en-US,en;q=0.5
Cookie: C2A=bgT%2C2%2C13; I1K=005930069500114800005490012330000660005380032830; FBA=140047446265697226; RMID=0e21f6d353798b60; F2G=N
Connection: keep-alive
"""

req = req.strip ().replace ("\n", "\r\n") + "\r\n\r\n"
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("image.moneta.co.kr", 80))
print(s.send(req))	
data = s.recv(65535)
print(len (data), repr(data))
data = s.recv(65535)
print(len (data), repr(data [:30]))

time.sleep (10)


print(s.send(req))	
data = s.recv(65535)
print(len (data), repr(data))
data = s.recv(65535)
print(len (data), repr(data [:30]))


s.close()

