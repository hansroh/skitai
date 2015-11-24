import re, sys, os
from urllib.parse import unquote, unquote_plus
import json

####################################################################################
# Utitlities
####################################################################################
REQUEST = re.compile (b'([^ ]+) ([^ ]+)(( HTTP/([0-9.]+))$|$)')
CONNECTION = re.compile (b'Connection: (.*)', re.IGNORECASE)

def crack_query (r):
	if not r: return {}
	if r[0]==b'?': r=r[1:]	
	arg={}
	q = [x.split(b'=', 1) for x in r.split(b'&')]	
	
	for each in q:
		k = unquote_plus (each[0])
		try: 
			t, k = k.split (b":", 1)
		except ValueError:
			t = b"str"
			
		if len (each) == 2:		
			v = unquote_plus(each[1])
			if t == b"str":
				pass
			elif t == b"int":
				v = int (v)
			elif t == b"float":
				v = float (v)
			elif t == b"list":
				v = v.split (b",")
			elif t == b"bit":
				v = v.lower () in (b"1", b"true", b"yes")
			elif t == b"json":
				v = json.loads (v)
				
		else:
			v = ""			
			if t == b"str":
				pass
			elif t == b"int":
				v = 0
			elif t == b"float":
				v = 0.0
			elif t == b"list":
				v = []
			elif t == b"bit":
				v = False
			elif t == b"json":
				v = {}
				
		if k in arg:
			if type (arg [k]) is not type ([]):
				arg[k] = [arg[k]]
			arg[k].append (v)
			
		else:
			arg[k] = v
			
	return arg

def crack_request (r):
	m = REQUEST.match (r)
	if m.end() == len(r):		
		uri=m.group(2)		
		if m.group(3):
			version = m.group(5)
		else:
			version = None	
		return m.group(1).lower(), uri, version
	else:
		return None, None, None

def join_headers (headers):
	r = []
	for i in range(len(headers)):
		if headers[i][0] in b' \t':	
			r[-1] = r[-1] + headers[i][1:]
		else:
			r.append (headers[i])
	return r

def get_header (head_reg, lines, group=1):
	for line in lines:
		m = head_reg.match (line)
		if m and m.end() == len(line):
			return m.group (group)
	return b''

def get_header_match (head_reg, lines):
	for line in lines:
		m = head_reg.match (line)
		if m and m.end() == len(line):
			return m
	return b''		

def get_extension (path):
	dirsep = path.rfind (b'/')
	dotsep = path.rfind (b'.')
	if dotsep > dirsep:
		return path[dotsep+1:]
	else:
		return b''
	