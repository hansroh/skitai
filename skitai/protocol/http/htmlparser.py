from wissen import _wissen
import sgmlop
import urllib.request, urllib.parse, urllib.error
import urllib.parse
import types
import re

class FastParser:
	def __init__ (self, url):
		self.url = url
		self.frame = False
		self.in_noscript = False
		self.refresh = None
		self.anchors = []
		self.links = []
		self.images = []
		self.forms = []
		self.form = {}
		self.hn = {}
		self.charset = "iso-8859-1"
		
		self.getlinktext = False
		self.linktext = ""
		
		self.gettitle = False
		self.title = ""
		
		self.gethn = 0
		self.hntext = ""
	
	
	#-----------------------------------------------------------------------
	# ENTITY HANDLER
	#-----------------------------------------------------------------------	
	def handle_data (self, data):
		if self.getlinktext:
			self.linktext += data
		
		if self.gethn:
			self.hntext += data
		
		if self.gettitle:
			self.title += data
		
	def resolve_entityref (self, content):
		if content [:5] == "nbsp;":
			return "&" + content [5:]
		return "&" + content
			
	def finish_starttag (self, tag, attr):
		tag = tag.lower ()		
		nattr= {}
		for k, v in list(attr.items ()):
			nattr [k.lower ()] = v			
		attr = nattr
		try: 
			getattr (self, "handle_start_" + tag) (attr)
		except AttributeError:
			pass	
	
	def finish_endtag (self, tag):
		try:
			getattr (self, "handle_end_" + tag) ()
		except AttributeError:
			pass	
	
	
	#-----------------------------------------------------------------------
	# TAG HANDLER
	#-----------------------------------------------------------------------
	def handle_end_form (self):	
		self.forms.append (self.form)
		self.form = {}
	
	def handle_start_h1 (self, attr):			
		if not self.gethn: self.gethn = 1
	
	def handle_start_h2 (self, attr):			
		if not self.gethn: self.gethn = 2
	
	def handle_start_h3 (self, attr):			
		if not self.gethn: self.gethn = 3
		
	def handle_start_h4 (self, attr):			
		if not self.gethn: self.gethn = 4
		
	def handle_start_h5 (self, attr):			
		if not self.gethn: self.gethn = 5
	
	def handle_start_h6 (self, attr):			
		if not self.gethn: self.gethn = 6
	
	def handle_end_h1 (self):			
		self.commit_hn ()
	
	def handle_end_h2 (self):			
		self.commit_hn ()
	
	def handle_end_h3 (self):			
		self.commit_hn ()
		
	def handle_end_h4 (self):			
		self.commit_hn ()
		
	def handle_end_h5 (self):			
		self.commit_hn ()
	
	def handle_end_h6 (self):			
		self.commit_hn ()
							
	def handle_end_td (self):
		self.commit_all ()
	
	def handle_end_tr (self):	
		self.commit_all ()
	
	def handle_end_table (self):	
		self.commit_all ()
				
	def handle_end_a (self):			
		self.commit_linktext ()
	
	def handle_start_title (self, attr):	
		self.gettitle = True
	
	def handle_end_title (self):	
		self.gettitle = False
					
	def handle_start_base (self, attr):	
		if "href" in attr:
			self.url = urllib.parse.urljoin (self.url, attr ["href"])
	
	def handle_start_frameset (self, attr):			
		self.frame = True
	
	def handle_start_frame (self, attr):	
		if "src" in attr:
			self.anchors.append (["frame", attr ["src"]])
	
	def handle_start_iframe (self, attr):	
		self.handle_start_frame (attr)
		
	def handle_start_meta (self, attr):
		if not self.in_noscript and "http-equiv" in attr:
			content = attr.get ("content", "")
			dcontent = {}
			if content:
				for each in content.split (";"):
					try:
						key, val = each.split ("=")
					except:
						dcontent [each.lower ()] = None
					else:
						dcontent [key.lower ()] = val.strip ()
						
			if attr ["http-equiv"].lower () == "content-type":
				nl = dcontent.get ("charset", "")
				if nl: 
					self.charset = nl
				
			elif attr ["http-equiv"].lower () == "refresh":
				nl = dcontent.get ("url", "")			
				if nl != self.url:
					self.refresh = urllib.parse.urljoin (self.url, nl)
						
	
	def handle_start_img (self, attr):		
		if "src" in attr:
			self.images.append (attr ["src"])
	
	def handle_start_a (self, attr):		
		self.commit_linktext ()				
		if "href" in attr:
			self.anchors.append (["", attr ["href"]])				
			self.getlinktext = True
	
	def handle_start_link (self, attr):		
		if "href" in attr:
			self.links.append ([attr.get ("title", ""), attr ["href"]])
			
	def handle_start_form (self, attr):		
		self.form = {
			"action": urllib.parse.urljoin (self.url, attr.get ("action", self.url)),
			"method": attr.get ("method", "get").lower (),
			"name": attr.get ("name", ""),
			"data": {}
		}
	
	def handle_start_select (self, attr):	
		name = attr.get ("name", "")
		if not name: return
		self.newform ()
		self.form ["data"] [attr.get ("name", "")]	 = ""
		
	def handle_start_textarea (self, attr):	
		name = attr.get ("name", "")
		if not name: return
		self.newform ()
		self.form ["data"] [attr.get ("name", "")]	 = ""
	
	def handle_start_input (self, attr):			
		name = attr.get ("name", "")
		if not name: return
		
		self.newform ()
		data = self.form ["data"]
		t = attr.get ("type", "text")
		if t in ("text", "hidden", "submit", "button", "image", "password"):
			data [name]	 = attr.get ("value", "")
		elif t in ("radio", "checkbox"):
			if "checked" in attr:
				data [name] = attr.get ("value", "")
	
	
	def handle_start_noscript (self, attr):
		self.in_noscript = True
		
	def handle_end_noscript (self):	
		self.in_noscript = False
		
	#-----------------------------------------------------------------------
	# SPECIAL FUNCS
	#-----------------------------------------------------------------------
	def finalize (self):
		if self.form:
			self.handle_end_form ()

	def newform (self):
		if not self.form:
			self.form = {
				"action": self.url,
				"method": "get",
				"name": "",
				"data": {}
			}
	
	def commit_all (self):
		for method in dir (self):
			if method != "commit_all" and method [:6] == "commit":
				getattr (self, method) ()
						
	def commit_linktext (self):
		if self.getlinktext and self.anchors:
			self.anchors [-1][0] = self.linktext
			self.linktext = ""	
			self.getlinktext = False
	
	def commit_hn (self):
		if self.gethn:
			try:
				self.hn [self.gethn].append (self.hntext)
			except KeyError:
				self.hn [self.gethn] = [self.hntext]	
			self.hntext = ""	
			self.gethn = 0
			
	
def fastparse (html, url):
	#p = _wissen.XMLParser ()
	p = sgmlop.XMLParser ()
	hdr = FastParser (url)
	p.register (hdr)
	p.parse (html)
	p.close ()
	hdr.finalize ()
	del p
	return hdr	


class HtmlEntity:
	def __init__ (self, html, url):
		self.html = html
		self.url = url
		self.sax = fastparse (html, self.url)
	
	def __del__ (self):
		del self.html
		if self.sax:
			del self.sax
		
	def write (self, output):
		f = open (output, "w")
		f.write (self.html)
		f.close ()
		
	def refresh (self):
		self.sax = fastparse (self.html, self.url)
		
	def setContent (self, html, refresh = 1):
		self.html = html
		self.refresh ()
	
	def getTitle (self):
		return self.sax.title
	
	def getH (self, level):
		return self.sax.hn [level]
		
	def getContent (self):
		return self.html
			
	def getImages (self, resolve = 1):
		if not resolve:
			return self.sax.images
		else:
			return [urllib.parse.urljoin (self.sax.url, x) for x in self.sax.images]	

	def getLinks (self, resolve = 1):
		if not resolve:
			return self.sax.links
		else:
			return [(x [0], urllib.parse.urljoin (self.sax.url, x [1])) for x in self.sax.links]
		
	def getAnchors (self, resolve = 1):
		if not resolve:
			return self.sax.anchors
		else:
			return [(x [0], urllib.parse.urljoin (self.sax.url, x [1])) for x in self.sax.anchors]

	def getForms (self):
		return self.sax.forms
	
	def isFrame (self):
		return self.sax.frame
	
	def isMove (self):
		return self.sax.refresh
	
	def getBase (self):
		return self.sax.url
	
	def setBase (self, url):
		self.sax.url = url
		
	def getForm (self, index):
		if type (index) is bytes:
			for form in self.sax.forms:
				if index == form ["name"]:
					return form
			return {}	
			
		try:
			return self.sax.forms [index]
		except IndexError:
			return {}
	

def parse (content, url):
	return HtmlEntity (content, url)


if __name__ == "__main__":
	import urllib.request, urllib.parse, urllib.error
	htm = """\
	"""
	f = urllib.request.urlopen ("http://www.lagrandeobserver.com/")
	htm = f.read ()
	
	f = parse (htm, "http://www.lagrandeobserver.com/")
	print(f.getForms ())
	print(f.getForm ("supplier_search"))
	print(f.getLinks (1))
	print(f.getImages (1))
	print(f.isFrame ())
	print(f.isMove ())
	
	