import html5lib
import re
import lxml.etree
import lxml.html
import lxml.html.clean
import re
import traceback
from copy import deepcopy
import sys
from skitai.lib import strutil

TABSSPACE = re.compile(r'[\s\t]+')
def innerTrim(value):
	if strutil.is_str_like (value):
		# remove tab and white space
		value = re.sub(TABSSPACE, ' ', value)
		value = ''.join(value.splitlines())
		return value.strip()
	return ''
	
class Parser:
	@classmethod
	def from_string (cls, html):
		if strutil.is_str_like (html) and html.startswith('<?'):
			html = re.sub(r'^\<\?.*?\?\>', '', html, flags=re.DOTALL)				
		try:
			return lxml.html.fromstring(html)			
		except Exception:
			traceback.print_exc()
			return None
		
	@classmethod
	def to_string (cls, node):
		return lxml.etree.tostring(node)
	
	def by_xpath (cls, node, expression):
		items = node.xpath(expression)
		return items
	
	@classmethod
	def by_xpath_re (cls, node, expression):
		regexp_namespace = "http://exslt.org/regular-expressions"
		items = node.xpath(expression, namespaces={'re': regexp_namespace})
		return items
		
	@classmethod
	def by_css (cls, node, selector):
		return node.cssselect(selector)
	
	@classmethod
	def by_id (cls, node, idd):
		selector = '//*[@id="%s"]' % idd
		elems = node.xpath(selector)
		if elems:
			return elems[0]
		return None

	@classmethod
	def by_tag_attr (
			cls, node, tag=None, attr=None, value=None, childs=False):
		NS = "http://exslt.org/regular-expressions"
		# selector = tag or '*'
		selector = 'descendant-or-self::%s' % (tag or '*')
		if attr and value:
			selector = '%s[re:test(@%s, "%s", "i")]' % (selector, attr, value)		
		elems = node.xpath(selector, namespaces={"re": NS})
		# remove the root node
		# if we have a selection tag
		if node in elems and (tag or childs):
			elems.remove(node)
		return elems
	
	@classmethod
	def by_tag (cls, node, tag):
		return cls.by_tags (node, [tag])
	
	@classmethod
	def by_tags (cls, node, tags):
		selector = ','.join(tags)
		elems = cls.by_css (node, selector)
		# remove the root node
		# if we have a selection tag
		if node in elems:
			elems.remove(node)
		return elems
	
	@classmethod
	def prev_siblings (cls, node):
		nodes = []
		for c, n in enumerate (node.itersiblings(preceding=True)):
			nodes.append(n)
		return nodes
		
	@classmethod
	def prev_sibling (cls, node):
		nodes = []
		for c, n in enumerate (node.itersiblings(preceding=True)):
			nodes.append(n)
			if c == 0:
				break
		return nodes[0] if nodes else None
	
	@classmethod
	def next_siblings (cls, node):
		nodes = []
		for c, n in enumerate (node.itersiblings(preceding=False)):
			nodes.append(n)
		return nodes
		
	@classmethod
	def next_sibling (cls, node):
		nodes = []
		for c, n in enumerate (node.itersiblings(preceding=False)):
			nodes.append(n)
			if c == 0:
				break
		return nodes[0] if nodes else None
		
	@classmethod
	def get_attr (cls, node, attr=None):
		if attr:
			return node.attrib.get(attr, None)
		return node.attrib
	
	@classmethod
	def has_attr (cls, node, attr = None):		
		if attr:
			return attr in node.attrib
		return len (node.attrib) != 0
		
	@classmethod
	def del_attr (cls, node, attr=None):
		if attr:
			_attr = node.attrib.get(attr, None)
			if _attr:
				del node.attrib[attr]

	@classmethod
	def set_attr (cls, node, attr=None, value=None):
		if attr and value:
			node.set(attr, value)
					
	@classmethod
	def append_child (cls, node, child):
		node.append(child)

	@classmethod
	def child_nodes (cls, node):
		return list(node)

	@classmethod
	def child_nodes_with_text (cls, node):
		root = node
		# create the first text node
		# if we have some text in the node
		if root.text:
			t = lxml.html.HtmlElement()
			t.text = root.text
			t.tag = 'text'
			root.text = None
			root.insert(0, t)
		# loop childs
		for c, n in enumerate(list(root)):
			idx = root.index(n)
			# don't process texts nodes
			if n.tag == 'text':
				continue
			# create a text node for tail
			if n.tail:
				t = cls.create_element(tag='text', text=n.tail, tail=None)
				root.insert(idx + 1, t)
		return list(root)

	@classmethod
	def get_children (cls, node):
		return node.getchildren()
	
	@classmethod
	def get_parent (cls, node):
		return node.getparent()
		
	@classmethod
	def get_text (cls, node):
		txts = [i for i in node.itertext()]		
		return innerTrim(u' '.join(txts).strip())
	
	@classmethod
	def get_texts (cls, node, trim = True):
		if trim:
			return [i.strip () for i in node.itertext()]
		else:	
			return [i for i in node.itertext()]
	
	@classmethod
	def is_text_node (cls, node):
		return True if node.tag == 'text' else False
	
	@classmethod
	def get_tag (cls, node):
		return node.tag
	
	@classmethod
	def replace_tag (cls, node, tag):
		node.tag = tag

	@classmethod
	def strip_tags (cls, node, *tags):
		lxml.etree.strip_tags(node, *tags)
			
	@classmethod
	def drop_node (cls, node):
		nodes.drop_tag ()
	
	@classmethod
	def drop_tree (cls, node):
		nodes.drop_tree ()
	
	@classmethod
	def create_element (cls, tag='p', text=None, tail=None):
		t = lxml.html.HtmlElement()
		t.tag = tag
		t.text = text
		t.tail = tail
		return t

	@classmethod
	def get_comments (cls, node):
		return node.xpath('//comment()')
		
	@classmethod
	def text_to_para (cls, text):
		return cls.create_element ('p', text)
	
	@classmethod
	def outer_html (cls, node):
		e0 = node
		if e0.tail:
			e0 = deepcopy(e0)
			e0.tail = None
		return cls.to_string(e0)
			
	@classmethod
	def clean_html (cls, node):
		article_cleaner = lxml.html.clean.Cleaner()
		article_cleaner.javascript = True
		article_cleaner.style = True
		article_cleaner.allow_tags = [
			'a', 'span', 'p', 'br', 'strong', 'b',
			'em', 'i', 'tt', 'code', 'pre', 'blockquote', 'img', 'h1',
			'h2', 'h3', 'h4', 'h5', 'h6']
		article_cleaner.remove_unknown_tags = False
		return article_cleaner.clean_html (node)
	
	@classmethod
	def get_param (cls, node, attr, name):
		name = name.lower ()
		params = cls.get_attr (node, attr)
		for param in params.split (";"):
			param = param.strip ()
			if not param.lower ().startswith (name):
				continue
			
			val = param [len (name):].strip ()
			if not val: return ""
			if val [0] == "=":
				val = val [1:].strip ()
				if not val: return ""
			if val [0] in "\"'":
				return val [1:-1]
			return val		
	
def remove_control_characters (html):
	def str_to_int(s, default, base=10):
		if int(s, base) < 0x10000:
			if strutil.PY_MAJOR_VERSION == 2:
				return unichr(int(s, base))
			else:	
				return chr(int(s, base))				
		return default

	html = re.sub(r"&#(\d+);?", lambda c: str_to_int(c.group(1), c.group(0)), html)
	html = re.sub(r"&#[xX]([0-9a-fA-F]+);?", lambda c: str_to_int(c.group(1), c.group(0), base=16), html)
	html = re.sub(r"[\x00-\x08\x0b\x0e-\x1f\x7f]", "", html)	
	return html

def remove_non_asc (html):	
	html = re.sub(br"&#(\d+);?", "", html)
	html = re.sub(br"&#[xX]([0-9a-fA-F]+);?", "", html)
	html = re.sub(br"[\x00-\x08\x80-\xff]", "", html)	
	return html
	
	
RX_CAHRSET = re.compile (br"[\s;]+charset\s*=\s*['\"]?([-a-z0-9]+)", re.M) #"
RX_META = re.compile (br"<meta\s+.+?>", re.I|re.M)

def get_charset (html):	
	encoding = None
	pos = 0	
	while 1:	
		match = RX_META.search (html, pos)
		if not match: break
		#print (match.group ())	
		charset = RX_CAHRSET.findall (match.group ().lower ())
		if charset:			
			encoding = charset [0].decode ("utf8")			
			#print (encoding)		
			break
		pos = match.end ()		
	return encoding

def to_str (html, encoding):
	def try_generic_encoding (html):
		try:
			return html.decode ("utf8")
		except UnicodeDecodeError:	
			return html.decode ("iso8859-1")
	
	if encoding is None:
		encoding = get_charset (html)
	
	try:
		if not encoding:
			html = try_generic_encoding (html)
		else:
			try:
				html = html.decode (encoding)
			except LookupError:
				html = try_generic_encoding (html)
				
	except UnicodeDecodeError:
		return remove_non_asc (html)
		
	else:
		return remove_control_characters (html)
	
def html (html, baseurl, encoding = None):
	# html5lib rebuilds possibly mal-formed html	
	try:
		return lxml.html.fromstring (lxml.etree.tostring (html5lib.parse (html, encoding = encoding, treebuilder="lxml")), baseurl)	
	except ValueError:
		return lxml.html.fromstring (lxml.etree.tostring (html5lib.parse (to_str (html, encoding), treebuilder="lxml")), baseurl)	

def etree (html, encoding = None):
	try:
		return html5lib.parse (html, encoding = encoding, treebuilder="lxml")	
	except ValueError:	
		return html5lib.parse (to_str (html, encoding), treebuilder="lxml")	


if __name__ == "__main__":	
	from urllib.request import urlopen
	from contextlib import closing
	
	with closing(urlopen("http://www.drugandalcoholrehabhouston.com")) as f:
		build (f.read ())

