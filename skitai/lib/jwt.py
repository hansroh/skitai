from base64 import b64decode, b64encode
from hmac import new as hmac
import json
import hashlib
		
def get_claim (secret_key, token):
	header, claim, sig = token.split (".")
	jheader = json.loads (b64decode (header).decode ("utf8"))
	alg = jheader.get ("alg")	
	if not alg or alg [:2] != "HS":
		return	
	hash_method = getattr (hashlib, "sha" + alg [2:])	
	mac = hmac (secret_key, None, hash_method)
	mac.update (("%s.%s" % (header, claim)).encode ("utf8"))	
	if mac.digest() != b64decode (sig):
		return
	return json.loads (b64decode (claim).decode ("utf8"))
	
def gen_token (secret_key, claim, alg = "HS256"):
	header = b64encode (json.dumps ({"alg": alg, "typ": "JWT"}).encode ("utf8"))
	claim = b64encode (json.dumps (claim).encode ("utf8"))
	hash_method = getattr (hashlib, "sha" + alg [2:])	
	mac = hmac (secret_key, None, hash_method)
	mac.update (header + b"." + claim)
	sig = b64encode (mac.digest())
	return (header + b"." + claim + b"." + sig).decode ("utf8")


if __name__ == "__main__":
	sk = b"your_secret_key_for_JWT_authorization"
	token = gen_token (sk, {'user': 'Hans Roh', 'roles': ['user']}, "HS256")
	print (token)
	print (get_claim (sk, token))
	
	import requests
	f = requests.get (
		"http://127.0.0.1:5000/lufex",
		headers ={"Authorization": "Bearer %s" % token}
	)
	print (f)
