import os
import base64, quopri, re, sys
import mimetypes
import time
import smtplib
import smtplib, poplib, email, rfc822

def safe (s):
	return re.sub ('\s+', ' ', s.replace ('"', '')).strip ()


#######################################################################################
# Qmail detector
#######################################################################################
class Qmail:
	rx_email = re.compile ('<([a-z0-9@._]+)>:', re.I)
	rx_code = re.compile ('Remote host said: (.+)', re.I)
	def __init__ (self, msg):
		self.M = email.message_from_string (msg)			
		self.subject = self.M ['subject']
		self.fr = self.M ['from']
		self.date = self.M ['date']
		self.mimetype = self.M.get_content_type ()
		if self.date:
			self.date = time.strftime ('%Y%m%d', rfc822.parsedate (self.date))
	
	def check (self):
		email, code = None, None
		hasattn = 0
		
		if self.mimetype == 'multipart/report':
			email, code = self.report_type ()
			
		elif self.fr.find ('MAILER-DAEMON') > -1 or self.fr.find ('postmaster') > -1:
			if self.M.get_main_type () == 'multipart':
				email, code = self.detect ()
			else:
				data = self.M.get_payload (decode = 1)
				email, code = self._find_email (data)
			
		elif self.M.get_main_type () == 'multipart':
			hasattn = self.check_attachment ()
						
		return email, code, self.date, hasattn
	
	def get_subject (self):
		return self.subject
			
	def detect (self):
		for part in self.M.walk ():			
			if part.get_content_type == 'text/plain':
				data = part.get_payload (decode = 1)
				email, code = self._find_email (data)
				if email: return email, code
			else: 
				continue				
		return None, None		
	
	def _find_email (self, data):						
		p = data.find ('work out.')
		if p == -1: return None, None
		
		email, code = None, None
		match = self.rx_email.search (data, p)		
		if match: email = match.group(1)
		else: return None, None
		
		match = self.rx_code.search (data, p)
		if match: code = match.group(1)
		else: return None, None		
		return email, code
	
	def check_attachment (self):
		for part in self.M.walk ():
			if part.get_filename (): return 1
		return 0
				
	def report_type (self):
		email, code = None, None
		for part in self.M.walk ():
			mimetype = part.get_content_type ()
			if mimetype == 'text/plain':
				email = part ['final-recipient']
				code = part ['status']
				status = part ['action']
				if email != None:
					email = email.split (';') [-1].strip ()
				if code != None:	
					code = code.strip ()
				if status != None:
					code = code + ' ' + status
				if email and code:
					break	
		return email, code


#######################################################################################
# Mailsite detector
#######################################################################################
class MailSite (Qmail):
	pass


#######################################################################################
# Recieving data from POP3
#######################################################################################		
class RecvMail:
	def __init__ (self, server, userinfo):
		self.popserver = server
		self.user, self.pwd = userinfo.split ('/')
		self.connected = 0
		
	def stat (self):
		if not self.connected: self.connect ()
		return self.server.stat ()
	
	def delete (self, num):		
		if not self.connected: self.connect ()
		self.server.dele (num + 1)
		
	def connect (self):
		self.server = poplib.POP3(self.popserver)
		self.server.user(self.user)
		self.server.pass_(self.pwd)
		self.connected = 1
	
	def get (self, num):
		data = self.server.retr(num + 1)[1]			
		return "\r\n".join (data)
		
	def close (self):
		self.server.quit ()
		self.connected = 0


#######################################################################################
# Generating and Sending email
#######################################################################################		
class NewMail:
	def __init__ (self, subject, sender_name, sender_email, receiver_name, receiver_email):
		self.H = {}
		self.contents = []
		self.H ['MIME-Version'] = '1.0'
		self.H ['Date'] = self.rfc_date ()
		self.H ['X-Priority'] = '3'
		self.H ['X-MSMail-Priority'] = 'Normal'
		#self.H ['X-Mailer'] = 'Microsoft Outlook Express 6.00.2800.1409'
		#self.H ['X-MimeOLE'] = 'Produced By Microsoft MimeOLE V6.00.2900.2962'
	
		self.sender_email = sender_email.strip ()
		self.receiver_email = receiver_email.strip ()
		self.H ['Subject'] = subject
		if sender_name: self.H ['From'] = '"%s" <%s>' % (safe (sender_name), sender_email)
		else: self.H ['From'] = sender_email.strip()
		if receiver_name: self.H ['To'] = '"%s" <%s>' % (safe (receiver_name), receiver_email)
		else: self.H ['To'] = receiver_email.strip()
	
	def __setitem__ (self, k, v):
		self.H [k] = v
			
	def rfc_date (self):
		return time.strftime ('%a, %d %b %Y %H:%M:%S +0900', time.localtime (time.time ()))
		
	def encode (self, encoding, data):
		if encoding == "base64":
			data = base64.encodestring (data)
		elif encoding == "quoted-printable":
			data = quopri.encodestring (data)
		return data	
		
	def add_text (self, data, mimetype, charset = 'us-asc', encoding = "base64"):
		msg = (
			"Content-type: %s; \r\n\tcharset=\"%s\"\r\n"
			"Content-Transfer-Encoding: %s\r\n"
			"\r\n" % (mimetype, charset, encoding)
			)		
		msg += self.encode (encoding, data)
		self.contents.append (msg)
		
	def add_file (self, filename, mimetype):
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
	
	def add_inline (self, filename, mimetype, cid):
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
		
	def send (self, server, login = None, debug = 0):
		body = "\r\n".join (["%s: %s" % (k, v) for k, v in self.H.items ()]) + "\r\n"
		
		if len (self.contents) == 0: 
			raise AttributeError		
		elif len (self.contents) == 1:			
			body += self.contents [0]
		else:
			boundary = "----=_NextPart_000_0201_01C717DE.C4D8A760"
			body += "Content-type: multipart/alternative; \r\n\tboundary=\"%s\"\r\n\r\n" % boundary
			body += "This is a multi-part message in MIME format.\r\n\r\n"
			for content in self.contents:
				body += "--%s\r\n%s\r\n\r\n" % (boundary, content)
			body += "--%s--\r\n" % boundary
		
		return self._send (server, body, login, debug)
	
	def _send (self, smtpserver, msg, login = None, debug = 0):
		error_msg = ""
		server = None
		
		try:
			server = smtplib.SMTP (smtpserver)			
		except:
			error_msg = "Server Connection Falied"
			server = None
			
		if not server: return error_msg
			
		server.set_debuglevel (debug)
		if login:
			try:
				uid, pwd = login.split ("/")
				server.login (uid, pwd)
			except smtplib.SMTPHeloError:
				error_msg = "Helo Error"
			except:
				error_msg = "Authentication Error"
		
		if error_msg:		
			server.quit ()
			return error_msg
		
		try:
			server.sendmail(self.sender_email, self.receiver_email, msg)
		except smtplib.SMTPHeloError:
			error_msg = "Helo Error"
		except smtplib.SMTPDataError:
			error_msg = "Data Error"
		except smtplib.SMTPRecipientsRefused:
			error_msg = "Recipients Refused"	
		except smtplib.SMTPSenderRefused:
			error_msg = "Sender Refused"
		except:
			error_msg = "Unknown Error"
			
		server.quit()
		
		return error_msg
		
		
if __name__=="__main__":
	data="""Hi, 
I recieved your message today.

I promise your request is processed with very high priority.

Thanks.
	"""
	m = NewMail ("e-Mail Test", "Tester", "hansroh@lufex.com", "Hans Roh", "hansroh@gmail.com")
	m.add_text (data, "text/plain", "Windows-1252", "7bit")
	m.add_text (data, "text/html", "Windows-1252", "quoted-printable")
	print m.send ("192.168.1.99")
	
	
	