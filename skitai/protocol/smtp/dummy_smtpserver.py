import smtpd

class SMTPChannel(smtpd.SMTPChannel):
	def smtp_RCPT(self, arg):
		if not self.__mailfrom:
			self.push('503 Error: need MAIL command')
			return
		address = self.__getaddr('TO:', arg)
		if not address:
			self.push('501 Syntax: RCPT TO: <address>')
			return
		self.push('501 This system is not configured to relay mail')
	
class SMTPServer (smtpd.SMTPServer):		
	def handle_accept(self):
		conn, addr = self.accept()			
		channel = SMTPChannel(self, conn, addr)
	
	def process_message(self, peer, mailfrom, rcpttos, data):
		pass
		
		