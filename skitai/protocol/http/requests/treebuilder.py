import html5lib
import re
import lxml.etree
import lxml.html
import lxml.html.clean
import re
import traceback
from copy import deepcopy

TABSSPACE = re.compile(r'[\s\t]+')
def innerTrim(value):
	if type (value) is str:
		# remove tab and white space
		value = re.sub(TABSSPACE, ' ', value)
		value = ''.join(value.splitlines())
		return value.strip()
	return ''

	
class Parser:
	@classmethod
	def from_string (cls, html):
		if type (html) is str and html.startswith('<?'):
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
		return attr
	
	@classmethod
	def has_attr (cls, node):
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
					

def html (html, baseurl, encoding = None):
	# html5lib rebuilds possibly mal-formed html
	return lxml.html.fromstring (lxml.etree.tostring (html5lib.parse (html, encoding = encoding, treebuilder="lxml")), baseurl)	

def etree (html, encoding = None):
	return html5lib.parse (html, encoding = encoding, treebuilder="lxml")	


if __name__ == "__main__":	
	from urllib.request import urlopen
	from contextlib import closing
	
	with closing(urlopen("http://www.drugandalcoholrehabhouston.com")) as f:
		build (f.read ())

