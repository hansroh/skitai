# -*- Mode: Python; tab-width: 4 -*-

RCS_ID = '$Id: producers.py,v 1.10 1999/02/01 03:08:46 rushing Exp $'

import string
import time
import cStringIO
import gzip
import compressors
from threads import trigger
import mimetypes
import os

"""
A collection of producers.
Each producer implements a particular feature:  They can be combined
in various ways to get interesting and useful behaviors.

For example, you can feed dynamically-produced output into the compressing
producer, then wrap this with the 'chunked' transfer-encoding producer.
"""

class simple_producer:
	"producer for a string"
	def __init__ (self, data, buffer_size = 4096):
		self.data = data
		self.buffer_size = buffer_size

	def more (self):
		if len (self.data) > self.buffer_size:
			result = self.data[:self.buffer_size]
			self.data = self.data[self.buffer_size:]
			return result
		else:
			result = self.data
			self.data = ''
			return result

class scanning_producer:
	"like simple_producer, but more efficient for large strings"
	def __init__ (self, data, buffer_size = 4096):
		self.data = data
		self.buffer_size = buffer_size
		self.pos = 0

	def more (self):
		if self.pos < len(self.data):
			lp = self.pos
			rp = min (
				len(self.data),
				self.pos + self.buffer_size
				)
			result = self.data[lp:rp]
			self.pos = self.pos + len(result)
			return result
		else:
			return ''

class lines_producer:
	"producer for a list of lines"

	def __init__ (self, lines):
		self.lines = lines

	def ready (self):
		return len(self.lines)

	def more (self):
		if self.lines:
			chunk = self.lines[:50]
			self.lines = self.lines[50:]
			return string.join (chunk, '\r\n') + '\r\n'
		else:
			return ''

class buffer_list_producer:
	"producer for a list of buffers"

	# i.e., data == string.join (buffers, '')
	
	def __init__ (self, buffers):

		self.index = 0
		self.buffers = buffers

	def more (self):
		if self.index >= len(self.buffers):
			return ''
		else:
			data = self.buffers[self.index]
			self.index = self.index + 1
			return data

class file_producer:
	"producer wrapper for file[-like] objects"

	# match http_channel's outgoing buffer size
	out_buffer_size = 4096

	def __init__ (self, file):
		self.done = 0
		self.file = file

	def more (self):
		if self.done:
			return ''
		else:
			data = self.file.read (self.out_buffer_size)
			if not data:
				self.file.close()
				del self.file
				self.done = 1
				return ''
			else:
				return data


"""-----------------------------286502649418924
Content-Disposition: form-data; name="submit-hidden"

Genious
-----------------------------286502649418924
Content-Disposition: form-data; name="submit-name"

Hans Roh
-----------------------------286502649418924
Content-Disposition: form-data; name="file1"; filename="House.2x01.acceptance.DVDRip-iMa.smi"
Content-Type: application/smil

asdadasda
-----------------------------286502649418924
Content-Disposition: form-data; name="file2"; filename=""
Content-Type: application/octet-stream


-----------------------------286502649418924--"""
class multipart_producer:
	ac_out_buffer_size = 1<<16
	
	def __init__ (self, data, boundary):
		# self.data = {"name": "Hans Roh", "file1": <open (path, "rb")>}
		self.data = data
		serf.dlist = []
		self.boundary = boundary
		self.current_file = None
		self.content_length = self.calculate_size ()
		
	def calculate_size (self):
		size = (len (self.boundary) + 2) * (len (self.data) + 1) + 2 # first -- and last --
		for name, value in self.data.items ():
			size += (41 + len (name)) #Content-Disposition: form-data; name=""\r\n
			if type (value) is not type (""):
				fsize = os.path.getsize (f.name)
				size += (fsize + 2) # file size + \r\n
				fn = os.path.split (f.name) [-1]
				size += len (fn) + 13 # ; filename=""
				mimetype = mimetypes.guess_type (fn) [0]
				if not mimetype:
					mimetype = "application/octet-stream"
				size += (16 + len (mimetype)) # Content-Type: application/octet-stream\r\n				
				value.close ()
				self.dlist.append (1, name, (fn, mimetype))
			else:
				self.dlist.append (0, name, value)				
			size += 2 # header end
		return size	

	def get_content_length (self):
		return self.content_length
		
	def more (self):
		if not self.dlist: 
			return ''
			
		if self.current_file:
			d = self.current_file.read (self.ac_out_buffer_size)
			if not d:
				self.current_file.close ()
				self.current_file = None
				self.dlist.pop (0)
				d = "\r\n"
				if not self.dlist:
					d += "--%s--" % self.boundary					
			return d
			
		if self.dlist:
			first = self.dlist [0]
			if first [0] == 0: # formvalue
				d = '--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (self.boundary, first [1], first [2])
				self.dlist.pop (0)
				if not self.dlist:
					d += "--%s--" % self.boundary
				return d	
			else:				
				self.current_file = open (fisrt [2], "rb")
				return '--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\n\r\n%s\r\nContent-Type: %s\r\n\r\n' % (
					self.boundary, first [1], first [2][0], first [2][1]
				)
		

# A simple output producer.  This one does not [yet] have
# the safety feature builtin to the monitor channel:  runaway
# output will not be caught.

# don't try to print from within any of the methods
# of this object.

class output_producer:
	"Acts like an output file; suitable for capturing sys.stdout"
	def __init__ (self):
		self.data = ''
			
	def write (self, data):
		lines = string.splitfields (data, '\n')
		data = string.join (lines, '\r\n')
		self.data = self.data + data
		
	def writeline (self, line):
		self.data = self.data + line + '\r\n'
		
	def writelines (self, lines):
		self.data = self.data + string.joinfields (
			lines,
			'\r\n'
			) + '\r\n'

	def ready (self):
		return (len (self.data) > 0)

	def flush (self):
		pass

	def softspace (self, *args):
		pass

	def more (self):
		if self.data:
			result = self.data[:512]
			self.data = self.data[512:]
			return result
		else:
			return ''
			

class stream_producer:
	"""
	In a threading, push data to channel directly until closed
	But is it better ajax loop call?
	
	def route (was):
		response = producers.stream_producer ()
		threading.Thread (target = some_work, args = (response, ...)).start ()
		return response
	
	def some_work (response):
		response.push (str)
		response.push (str)
		...
		response.close ()
		
	"""	
	def __init__ (self, channel, buffer_size = 4096):
		self.data = []
		self.channel = channel
		self.buffer_size = buffer_size
		self.closed = False
	
	def abort (self):
		self.close ()
			
	def push (self, data):
		if self.closed:
			raise Exception ("Channel Closed")
		self.data.append (data)
		trigger.wakeselect ()
			
	def ready (self):
		return (len (self.data) > 0) or self.closed

	def more (self):
		if not self.data:
			return ""
		
		require = self.buffer_size
		d = ""
		while self.data:
			result = self.data.pop (0)
			a, r = result [:require], result [require:]
			
			if r:
				self.data.insert (0, r)
				return a			
			
			d += a
			require -= len (a)			
			if require == 0:
				return d
				
		return d			
	
	def close (self):
		self.closed = True
		self.channel.ready = None
		self.data = []
		
		
class composite_producer:
	"combine a fifo of producers into one"
	def __init__ (self, producers):
		self.producers = producers

	def more (self):
		while len(self.producers):
			p = self.producers.first()
			d = p.more()
			if d:
				return d
			else:
				self.producers.pop()
		else:
			return ''

class globbing_producer:
	"""
	'glob' the output from a producer into a particular buffer size.
	helps reduce the number of calls to send().  [this appears to
	gain about 30% performance on requests to a single channel]
	"""

	def __init__ (self, producer, buffer_size = 4096):
		self.producer = producer
		self.buffer = ''
		self.buffer_size = buffer_size

	def more (self):
		while len(self.buffer) < self.buffer_size:
			data = self.producer.more()
			if data:
				self.buffer = self.buffer + data
			else:
				break
		r = self.buffer
		self.buffer = ''
		return r


class hooked_producer:
	"""
	A producer that will call <function> when it empties,.
	with an argument of the number of bytes produced.  Useful
	for logging/instrumentation purposes.
	"""

	def __init__ (self, producer, function):
		self.producer = producer
		self.function = function
		self.bytes = 0

	def more (self):
		#print "hooked_producer.more ()"
		if self.producer:
			result = self.producer.more()
			if not result:
				self.producer = None
				self.function (self.bytes)
			else:
				self.bytes = self.bytes + len(result)
			return result
		else:
			return ''

# HTTP 1.1 emphasizes that an advertised Content-Length header MUST be
# correct.  In the face of Strange Files, it is conceivable that
# reading a 'file' may produce an amount of data not matching that
# reported by os.stat() [text/binary mode issues, perhaps the file is
# being appended to, etc..]  This makes the chunked encoding a True
# Blessing, and it really ought to be used even with normal files.
# How beautifully it blends with the concept of the producer.

class chunked_producer:
	"""A producer that implements the 'chunked' transfer coding for HTTP/1.1.
	Here is a sample usage:
		request['Transfer-Encoding'] = 'chunked'
		request.push (
			producers.chunked_producer (your_producer)
			)
		request.done()
	"""

	def __init__ (self, producer, footers=None):
		self.producer = producer
		self.footers = footers
	
	def more (self):
		if self.producer:
			data = self.producer.more()
			#print "------------", len (data)
			if data:
				return '%x\r\n%s\r\n' % (len(data), data)
			else:				
				self.producer = None
				if self.footers:
					return string.join (
						['0'] + self.footers,
						'\r\n'
						) + '\r\n\r\n'
				else:
					return '0\r\n\r\n'
		else:
			return ''

# Unfortunately this isn't very useful right now (Aug 97), because
# apparently the browsers don't do on-the-fly decompression.  Which
# is sad, because this could _really_ speed things up, especially for
# low-bandwidth clients (i.e., most everyone).

try:
	import zlib
except ImportError:
	zlib = None

class compressed_producer:
	"""
	Compress another producer on-the-fly, using ZLIB
	[Unfortunately, none of the current browsers seem to support this]
	"""

	# Note: It's not very efficient to have the server repeatedly
	# compressing your outgoing files: compress them ahead of time, or
	# use a compress-once-and-store scheme.  However, if you have low
	# bandwidth and low traffic, this may make more sense than
	# maintaining your source files compressed.
	#
	# Can also be used for compressing dynamically-produced output.

	def __init__ (self, producer, level=6):
		self.producer = producer
		self.compressor = zlib.compressobj (level, zlib.DEFLATED)
			
	def more (self):
		if self.producer:
			cdata = ''
			# feed until we get some output
			while not cdata:
				data = self.producer.more()
				if not data:
					self.producer = None
					return self.compressor.flush()
				else:
					cdata = self.compressor.compress (data)					
			return cdata
		else:
			return ''


class gzipped_producer (compressed_producer):
	def __init__ (self, producer, level=5):
		self.producer = producer
		self.compressor = compressors.GZipCompressor (level)
	
	
class escaping_producer:

	"A producer that escapes a sequence of characters"
	" Common usage: escaping the CRLF.CRLF sequence in SMTP, NNTP, etc..."

	def __init__ (self, producer, esc_from='\r\n.', esc_to='\r\n..'):
		self.producer = producer
		self.esc_from = esc_from
		self.esc_to = esc_to
		self.buffer = ''
		from asynchat import find_prefix_at_end
		self.find_prefix_at_end = find_prefix_at_end

	def more (self):
		esc_from = self.esc_from
		esc_to   = self.esc_to

		buffer = self.buffer + self.producer.more()

		if buffer:
			buffer = string.replace (buffer, esc_from, esc_to)
			i = self.find_prefix_at_end (buffer, esc_from)
			if i:
				# we found a prefix
				self.buffer = buffer[-i:]
				return buffer[:-i]
			else:
				# no prefix, return it all
				self.buffer = ''
				return buffer
		else:
			return buffer


class fifo:
	def __init__ (self, list=None):
		if not list:
			self.list = []
		else:
			self.list = list
		
	def __len__ (self):
		return len(self.list)

	def first (self):
		return self.list[0]

	def push_front (self, object):
		self.list.insert (0, object)

	def push (self, data):
		self.list.append (data)

	def pop (self):
		if self.list:
			result = self.list[0]
			del self.list[0]
			return (1, result)
		else:
			return (0, None)

			