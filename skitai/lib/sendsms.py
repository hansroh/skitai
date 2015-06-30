import base64
import urllib
from skitai.lib import timeoutsocket

timeoutsocket.setDefaultSocketTimeout (60)

def send (uid, password, rp, msg = "", sp = "02-581-3424"):
	msuid = base64.encodestring ("iwizkrsms")[:-1]
	smspwd = base64.encodestring ("remem0523")[:-1]
	smsurl = "http://sms.iwizkrsms.cafe24.com/sms_send_new.php?user_id=%s&passwd=%s" % (msuid, smspwd)
	smsurl += "&mode=" + base64.encodestring ("1")[:-1]
	smsurl += "&nointeractive=" + base64.encodestring ("1")[:-1]
	smsurl += "&testflag=" + base64.encodestring ("Y")[:-1]
	smsurl += "&rphone=" + base64.encodestring (rp)[:-1]
	
	sp = sp.split ("-")
	assert len (sp) == 3
	for i in range (len (sp)):
		smsurl += "&sphone%d=%s" % (i + 1, base64.encodestring (sp [i])[:-1])
	
	smsurl += "&msg=%s" % urllib.quote (base64.encodestring (msg)[:-1])
	print smsurl
	f = urllib.urlopen (smsurl)
	print `f.read ()`
	
	#http://sms.iwizkrsms.cafe24.com/sms_send_new.php?user_id=aXdpemtyc21z&passwd=cmVtZW0wNTIz&mode=MQ==&rphone=MDEwNDYwMjExNjU=&sphone1=MDI=&sphone2=NTgx&sphone3=MzQyNA==&msg=vsiz58fPvLy%2F5LOqtMLAscXCx%2FbA1LTPtNk%3D


if __name__ == "__main__":
	send ("iwizkrsms", "remem0523", "01046021165", "Server maybe daed")
	pass
