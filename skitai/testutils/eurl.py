from skitai.protocol.http import eurl

def test_crack_uql():
	d = (
		  "POST http://hans:whddlgkr@target_site.com:8089/rpc2/agent.status?a=x#eter "		  
		  "--head-User-Agent Machine 1.4 head-Connection close "
		  "--head-Content-Type text/xml; chatser=utf16 "
		  "--http-version 1.3 "
		  "--http-proxy 127.0.0.1:5000 "
		  "--http-form key=val,/=+ 1 "
		  "--with-cid 456"
		  )
	el = eurl.EURL (d)
	el.show ()
	print el.make_request_header ()
	
	

if __name__ == "__main__":
	test_crack_uql ()
