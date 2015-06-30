from email import Parser
from email import Message
from email import Errors
import cStringIO
import re
from string import *
import rfc822, time

NL = '\n'
def decode(value):
	rx_range=re.compile('=\?.+?\?([BQUbqu])\?.*?\?=', re.S)	
	rx_remove=re.compile('=\?.+?\?([BQUbqu])\?', re.S)	
	match=rx_range.search(value)
	if not match: return value
	
	valuestack=[]
	while 1:
		match=rx_range.search(value)
		if match:
			valuestack.append(value[:match.start()])			
			buffer=value[match.start():match.end()]
			value=value[match.end():]
			encoding=upper(match.group(1))
			buffer=rx_remove.sub('',buffer)[:-2]			
			input=cStringIO.StringIO()
			output=cStringIO.StringIO()	
			input.write(buffer)
			input.seek(0)
			if encoding == 'B':
				import base64
				base64.decode(input, output)
			if encoding == 'Q':
				import quopri
				quopri.decode(input, output)
			if encoding == 'U':
				import uu
				uu.decode(input, output)	
			buffer=output.getvalue()
			input.close()
			output.close()
			valuestack.append(buffer)	
		else:
			valuestack.append(value)	
			break
			
	return ''.join(valuestack)
	
	
class smart_Message(Message.Message):
	def get_addr(self, name):
		data=self[name]
		if data:
			a = rfc822.AddrlistClass(data)
			addrlist=a.getaddrlist()
			if not addrlist: return [(None, None)]	
			return addrlist
		else: return [(None, None)]	
	
	def get_date(self, name):        
		data = self[name]
		if data:
			#data = replace(data,'.',':')
			date = rfc822.parsedate_tz(data)			
			try:
				date = rfc822.mktime_tz (date)
				date = time.gmtime (date)
				date=time.strftime('%Y/%m/%d %H:%M:%S', date)
			except: return None			
			return date			
		else: return None

		
class smart_Parser(Parser.Parser):
	def __init__(self, _class=smart_Message):
		self._class = _class

	def parse(self, fp):
		root = self._class()
		self._parseheaders(root, fp)
		self._parsebody(root, fp)
		return root

	def parsestr(self, text):
		return self.parse(cStringIO.StringIO(text))
	
	def _parseheaders(self, container, fp):
		# Parse the headers, returning a list of header/value pairs.  None as
		# the header means the Unix-From header.
		lastheader = ''
		lastvalue = []
		lineno = 0
		while 1:
			line = fp.readline()[:-1]
			if not line or not line.strip():
				break
			lineno += 1
			# Check for initial Unix From_ line
			if line.startswith('From '):
				if lineno == 1:
					container.set_unixfrom(line)
					continue
				else:
					continue
					#raise Errors.HeaderParseError('Unix-from in headers after first rfc822 header')
			#
			# Header continuation line
			if line[0] in ' \t':
				if not lastheader:
					continue
					#raise Errors.HeaderParseError('Continuation line seen before first header')
				lastvalue.append(line)
				continue
			# Normal, non-continuation header.  BAW: this should check to make
			# sure it's a legal header, e.g. doesn't contain spaces.  Also, we
			# should expose the header matching algorithm in the API, and
			# allow for a non-strict parsing mode (that ignores the line
			# instead of raising the exception).
			i = line.find(':')
			if i < 0:
				continue
				#raise Errors.HeaderParseError('Not a header, not a continuation')
			if lastheader:
				try: container[lastheader] = decode(NL.join(lastvalue))
				except: container[lastheader] = NL.join(lastvalue)
			lastheader = line[:i]
			lastvalue = [line[i+1:].lstrip()]
		# Make sure we retain the last header
		if lastheader:
			try: container[lastheader] = decode(NL.join(lastvalue))
			except: container[lastheader] = NL.join(lastvalue)
			
	def _parsebody(self, container, fp):
		boundary = container.get_boundary()
		isdigest = (container.get_type() == 'multipart/digest')
		if boundary:
			preamble = epilogue = None
			separator = '--' + boundary
			payload = fp.read()
			start = payload.find(separator)
			if start < 0:
				container.add_payload(payload)
				return
			if start > 0:
				preamble = payload[0:start]
			start += len(separator) + 1 + isdigest
			terminator = payload.find('\n' + separator + '--', start)
			if terminator < 0:
				terminator = len(payload)
			if terminator + len(separator) + 3 < len(payload):
				epilogue = payload[terminator + len(separator) + 3:]
			if isdigest:
				separator += '\n\n'
			else:
				separator += '\n'
			parts = payload[start:terminator].split('\n' + separator)
			for part in parts:
				if type(part) is type('') and not part.strip():
					parts.remove(part)
				elif part:
					msgobj = self.parsestr(part)
					container.preamble = preamble
					container.epilogue = epilogue
					if not isinstance(container.get_payload(), type([])):
						container.set_payload([msgobj])
					else:
						container.add_payload(msgobj)
		
		elif container.get_main_type() == 'message':
			# Create a container for the payload, 
   			# but watch out for there not
			# being any headers left
			try:
				msg = self.parse(fp)
			except Errors.HeaderParseError:
				msg = self._class()
				self._parsebody(msg, fp)
			container.add_payload(msg)
			
		else:
			container.add_payload(fp.read())
			