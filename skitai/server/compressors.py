import zlib
import gzip
import cStringIO
import time
import struct

class DeflateCompressor:
	def __init__ (self, level = 5):
		self.compressor = zlib.compressobj (5)	
		
	def compress (self, buf):	
		return self.compressor.compress (buf)
	
	def flush (self):
		return self.compressor.flush ()
		

class GZipCompressor:
	HEADER = "\037\213\010" + chr (0) + struct.pack ("<L", long (time.time ())) + "\002\377"
	def __init__ (self, level = 5):
		self.size = 0
		self.crc = zlib.crc32("")
		self.compressor = zlib.compressobj (level, zlib.DEFLATED, -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)
		self.first_data = True
			
	def compress (self, buf):	
		self.size = self.size + len(buf)
		self.crc = zlib.crc32(buf, self.crc)
		d = self.compressor.compress (buf)
		if self.first_data:
			d = self.HEADER + d
			self.first_data = False
		return d	
	
	def flush (self):
		d = self.compressor.flush ()
		return d + struct.pack ("<l", self.crc) + struct.pack ("<L", self.size & 0xFFFFFFFFL)
		

def U32(i):
	if i < 0:
		i += 1L << 32
	return i
    
class GZipDecompressor:	
	def __init__ (self, level = 5):
		self.size = 0
		self.crc = zlib.crc32("")
		self.decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
		self.first_data = True
		self.maybe_eof = ""
			
	def decompress (self, buf):
		if self.first_data:
			buf = buf [10:]
			self.first_data = False		
		
		if len (buf) > 8:
			self.maybe_eof = buf [-8:]	
		else:
			self.maybe_eof += buf
			self.maybe_eof = self.maybe_eof [-8:]
								
		d = self.decompressor.decompress (buf)		
		self.size += len (d)
		self.crc = zlib.crc32(d, self.crc)
		if d == "":
			return self.decompressor.flush ()
		return d
	
	def flush (self):
		crcs, isizes = self.maybe_eof [:4], self.maybe_eof [4:]
		crc32 = struct.unpack ("<l", crcs)[0]
		isize = U32 (struct.unpack ("<L", isizes)[0])
		if U32 (crc32) != U32 (self.crc):
			raise IOError, "CRC check failed"
		elif isize != (self.size & 0xFFFFFFFFL):
			raise IOError, "Incorrect length of data produced"
		return ""
			

if __name__ == "__main__":
	import urllib
	f =urllib.urlopen ("http://www.gmarket.co.kr/index.asp/")
	d = f.read ()
	
	a = GZipCompressor ()
	x = a.compress (d) + a.flush ()	
	b = GZipDecompressor ()	
	while x:
		k, x = x [:10], x [10:]		
		b.decompress (k)
	print 		`b.flush ()`
	print 		`b.flush ()`
	print 		`b.flush ()`	
	a = zlib.compressobj ()
	x = a.compress (d) + a.flush ()	
	b = zlib.decompressobj ()	
	while x:
		k, x = x [:10], x [10:]				
		b.decompress (k)
	b.decompress ("")	
	b.decompress ("")	
	print 		`b.flush ()`
	print 		`b.flush ()`
	print 		`b.flush ()`
	
