import json
import sys
from datetime import date
from xmlrpc import client

def catch (format = 0, exc_info = None):
	if exc_info is None:
		exc_info = sys.exc_info()
	t, v, tb = exc_info
	tbinfo = []
	assert tb # Must have a traceback
	while tb:
		tbinfo.append((
			tb.tb_frame.f_code.co_filename,
			tb.tb_frame.f_code.co_name,
			str(tb.tb_lineno)
			))
		tb = tb.tb_next

	del tb
	file, function, line = tbinfo [-1]
	
	# format 0 - text
	# format 1 - html
	# format 2 - list
	try:
		v = str (v)
	except:
		v = repr (v)
		
	if format == 1:
		if v.find ('\n') != -1:
			v = v.replace ("\r", "").replace ("\n", "<br>")
		buf = ["<h3>%s</h3><h4>%s</h4>" % (t.__name__.replace (">", "&gt;").replace ("<", "&lt;"), v)]
		buf.append ("<b>at %s at line %s, %s</b>" % (file, line, function == "?" and "__main__" or "function " + function))
		buf.append ("<ul type='square'>")
		buf += ["<li>%s <span class='f'>%s</span> <span class='n'><b>%s</b></font></li>" % x for x in tbinfo]
		buf.append ("</ul>")		
		return "\n".join (buf)

	buf = []
	buf.append ("%s %s" % (t, v))
	buf.append ("in file %s at line %s, %s" % (file, line, function == "?" and "__main__" or "function " + function))
	buf += ["%s %s %s" % x for x in tbinfo]
	if format == 0:
		return "\n".join (buf)
	return buf	

	
class DateEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, date):
			return str(obj)			
		return json.JSONEncoder.default(self, obj)
		
			
class API:
	def __init__ (self, request, data = None):
		self.request = request # for response typing 
		self.data = data or {}
		self.content_type = self.set_content_type ()
		
	def __setitem__ (self, k, v):
		self.set (k, v)
	
	def __getitem__ (self, k, v = None):
		return self.get (k, v)
	
	def set (self, k, v):
		self.data [k] = v
	
	def get (self, k, v = None):
		return self.data.get (k, )
	
	def get_content_type (self):
		return self.content_type
		
	def set_content_type (self):
		content_type = self.request.get_header ("accept", 'application/json')
		if not content_type.startswith ("text/xml"):			
			content_type = 'application/json'
		return content_type	
		
	def encode (self, charset):
		return self.to_string ().encode (charset)
	
	def __str__ (self):
		return self.to_string ()
		
	def to_string (self):
		if self.content_type.startswith ("text/xml"):
			return client.dumps ((self.data,))
		return json.dumps (self.data, cls = DateEncoder)
			
	def traceback (self, message = 'exception occured', code = 20000, debug = 'see traceback', more_info = None):
		self.error (message, code, debug, more_info, sys.exc_info ())
		
	def error (self, message, code = 20000, debug = None, more_info = None, exc_info = None):
		self.data = {}
		self.data ['code'] = code
		self.data ['message'] = message
		if debug:
			self.data ['debug'] = debug
		if more_info:
			self.data ['more_info'] = more_info
		if exc_info:
			self.data ["traceback"] = catch (2, exc_info)

