import os

class Handler:	
	def __init__ (self, wasc, html):
		self.wasc = wasc
		self.html = html
		self.size = 0
		self.mtime = 0
		self.msg = ""
	
	def match (self, request):
		return 1
			
	def readmsg (self):	
		size = os.path.getsize (self.html)
		if size != self.size:
			self.size = size
			return self.refresh ()
			
		mtime = os.path.getmtime (self.html)				
		if mtime != self.mtime:
			self.mtime = mtime
			self.refresh ()
	
	def refresh (self):		
		f = open (self.html)
		self.msg = f.read ()
		f.close ()
		
	def handle_request (self, request):
		self.readmsg ()
		request.reply_code = 503
		request.reply_message = "Service Unavailable"
		request['Content-Type'] = 'text/html'
		request['Retry-After'] = '3600'
		request.push (self.msg)
		request.done ()
		
		