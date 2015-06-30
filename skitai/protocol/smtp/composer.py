import os
import base64, quopri, re, sys
import mimetypes
import time
import email, rfc822

class InvalidEmail (Exception): pass

class Composer:
	def __init__ (self, subject = None, snd = None, rcpt = None, uid = None, fn = None, header = None):
		self.H = {}
		self.contents = []
		self.subject = subject
		self.snd = snd
		self.rcpt = rcpt
		self.fn = fn
		self.uid = uid
		self.__responsed = 0
		self.__got_file = 0
		
		self.set_default_header (header)
		if fn: 
			self.parseFile (fn)
		 	
	def set_default_header (self, header):
		self.set_header ('MIME-Version', '1.0')
		self.set_header ('X-Priority', '3')
		self.set_header ('X-Mailer', 'Email Delivery System')
		self.set_header ('Date', self.rfc_date ())		
		if self.subject: self.set_header ('Subject', self.subject.strip ())
		if self.rcpt: self.set_header ('To', self.rcpt.strip ())
		if self.snd: self.set_header ('From', self.snd.strip ())
		
		if header:
			for k, v in header.items (): 
				self.set_header (k, v)
	
	def rfc_date (self):
		return time.strftime ("%a, %d %b %Y %H:%m:%S -0500", time.localtime (time.time () - 3600 * 14))
	
	def parse_address (self, addr):
		try:
			return rfc822.parseaddr(addr)
		except AttributeError:
			return ("", addr)
				
	def encode (self, encoding, data):
		if encoding == "base64":
			data = base64.encodestring (data)
		elif encoding == "qp":
			data = quori.encodestring (data)
		return data	
	
	def set_header (self, name, value):
		self.H [name] = value
		
		
	#----------------------------------------------------------------
	# human interface
	#----------------------------------------------------------------
	def parseFile (self, fn):
		if self.__got_file:
			raise AssertionError, "file already parsed"
		
		self.fn = fn		
		f = open (fn)
		_uid = f.readline ().strip ()
		_snd = f.readline ().strip ()		
		if _snd.find ("@") == -1:
			raise InvalidEmail, "sender address is not valid"
		_rcpt = f.readline ().strip ()
		if _rcpt.find ("@") == -1:
			raise InvalidEmail, "reciever address is not valid"
		_subject = f.readline ().strip ()
		
		if not self.uid: 		
			self.uid = _uid
		if not self.snd: 		
			self.snd = _snd		
			self.set_header ('From', self.snd)
		if not self.rcpt:
			self.rcpt = _rcpt
			self.set_header ("To", self.rcpt)
		if not self.subject:
			self.subject = _subject
			self.set_header ("Subject", self.subject)
		
		data = f.read ()
		
		if fn [-4:] in (".htm", "html"):
			self.addText (data, "text/html")
		else:	
			self.addText (data, "text/plain")
			
		f.close ()
		
		self.__got_file = 1		
			
	def removeFile (self):
		if self.fn:
			try: os.remove (self.fn)
			except: pass
		
	def addText (self, data, mimetype, charset = 'us-asc', encoding = "base64"):
		if encoding not in ("base64", "qp", "8bit"): encoding = "base64"
						
		msg = (
			"Content-type: %s; charset=\"%s\"\r\n"
			"Content-Transfer-Encoding: %s\r\n"
			"\r\n" % (mimetype, charset, encoding)
			)		
		msg += self.encode (encoding, data)
		self.contents.append (msg)
		
	def addFile (self, filename, mimetype):
		name = os.path.split (filename) [-1]
		msg = (
			"Content-Type: %s; name=\"%s\"\r\n"
			"Content-transfer-encoding: base64\r\n"
			"Content-Disposition: attachment; filename=\"%s\"\r\n"
			"\r\n" % (name, mimetype, name)
			)
			
		data = open (filename, "rb").read ()
		msg += self.encode ("base64", data)
		self.contents.append (msg)
	
	def addInline (self, filename, mimetype, cid):
		name = os.path.split (filename) [-1]
		msg = (
			"Content-Type: %s; name=\"%s\"\r\n"
			"Content-transfer-encoding: base64\r\n"
			"Content-Disposition: inline; filename=\"%s\"\r\n"
			"Content-ID: %s\r\n"
			"\r\n" % (mimetype, name, name, cid)
			)
		
		data = open (filename, "rb").read ()
		msg += self.encode ("base64", data)
		self.contents.append (msg)
	
	
	#----------------------------------------------------------------
	# communicate from async client and agent
	#----------------------------------------------------------------
	def set_response	(self, code, resp):
		self.__code, self.__resp = code, resp
		self.__responsed = 1
	
	def get_response	(self):
		if self.__responsed:
			return self.uid, self.__code, self.__resp, self.get_TO ()
	
	
	#----------------------------------------------------------------
	# for AsyncSmtp
	#----------------------------------------------------------------
	def get_filename (self):
		return self.fn
	
	def get_sender (self):
		return self.snd
	
	def get_reciever (self):
		return self.rcpt
		
	def get_UID (self):
		return self.uid
			
	def get_TO (self):
		return self.parse_address (self.rcpt) [1]
	
	def get_FROM (self):
		return self.parse_address (self.snd) [1]
	
	def get_HOST (self):
		return self.parse_address (self.rcpt) [1].split ("@") [-1]
		
	def get_DATA (self):
		msg = "\r\n".join (["%s: %s" % (k, v) for k, v in self.H.items ()]) + "\r\n"
		
		if len (self.contents) == 0:
			raise AttributeError
			
		elif len (self.contents) == 1:
			msg += self.contents [0]
			
		else:
			boundary = '__________' + self.se.replace ('@', '_') + str (time.time ())
			msg += "Content-type: multipart/mixed; boundary=\"%s\"\r\n\r\n" % boundary
			for content in self.contents:
				msg += "--%s\r\n%s\r\n\r\n" % (boundary, content)
			msg += "--%s--\r\n" % boundary
		
		return msg
	
	
		
				
if __name__=="__main__":
	data="""
<b>testing!!!</b>
<img src="cid:x" border="3">
<br>
	"""
	file = "g:\\project\\nlcli\\temp\\aapla@aol.com.html"
	m = Composer ("Tester<hansroh@lufex.com>", fn = file)
	
	print m.getTO ()
	print m.getFROM ()
	print `m.getDATA () [:500]`
	