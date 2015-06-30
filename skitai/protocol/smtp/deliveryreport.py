import email
import re

class QmailReport:
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


class MailSiteReport (Qmail): pass


class POPRetrive:
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
		data = self.server.retr (num + 1)[1]			
		return "\r\n".join (data)
		
	def close (self):
		self.server.quit ()
		self.connected = 0
		
		
		