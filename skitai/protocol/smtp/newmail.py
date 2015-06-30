import os
import base64, quopri, re, sys
import mimetypes
import time
import smtplib
import smtplib, poplib, email, rfc822

def safe (s):
	return re.sub ('\s+', ' ', s.replace ('"', '')).strip ()
	
class NewMail:
	def __init__ (self, subject, sender_name, sender_email, receiver_name, receiver_email):
		self.H = {}
		self.contents = []
		self.H ['MIME-Version'] = '1.0'
		self.H ['Date'] = self.rfc_date ()
		#self.H ['X-Priority'] = '3'
		#self.H ['X-MSMail-Priority'] = 'Normal'
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

	def add_text (self, data, mimetype, charset = 'us-ascii', encoding = "7bit"):
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
			"\r\n" % (mimetype, name, name)
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
			curserver, curport = smtpserver.split (":")
			curport = int (curport)
		except (IndexError, TypeError, ValueError):
			curserver, curport = smtpserver, 25
				
		try:
			server = smtplib.SMTP (curserver, curport)				
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
