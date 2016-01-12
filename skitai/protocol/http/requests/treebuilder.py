import html5lib
import re
import lxml.etree
import lxml.html
import lxml.html.clean
from lxml.html import html5parser
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
	def xpath_re (cls, node, expression):
		regexp_namespace = "http://exslt.org/regular-expressions"
		items = node.xpath(expression, namespaces={'re': regexp_namespace})
		return items

	@classmethod
	def css_select (cls, node, selector):
		return node.cssselect(selector)
	
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
	def from_string (cls, html):
		if type (html) is str and html.startswith('<?'):
			html = re.sub(r'^\<\?.*?\?\>', '', html, flags=re.DOTALL)				
		try:
			return lxml.html.fromstring(html)			
		except Exception:
			traceback.print_exc()
			return None
		
	@classmethod
	def node_to_string (cls, node):
		return lxml.etree.tostring(node)

	@classmethod
	def replace_tag (cls, node, tag):
		node.tag = tag

	@classmethod
	def strip_tags (cls, node, *tags):
		lxml.etree.strip_tags(node, *tags)

	@classmethod
	def get_element_by_id (cls, node, idd):
		selector = '//*[@id="%s"]' % idd
		elems = node.xpath(selector)
		if elems:
			return elems[0]
		return None

	@classmethod
	def get_elements_by_tag (
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
	def text_to_para (cls, text):
		return cls.from_string(text)

	@classmethod
	def get_children (cls, node):
		return node.getchildren()

	@classmethod
	def get_elements_by_tags (cls, node, tags):
		selector = ','.join(tags)
		elems = cls.css_select(node, selector)
		# remove the root node
		# if we have a selection tag
		if node in elems:
			elems.remove(node)
		return elems

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
	def get_parent (cls, node):
		return node.getparent()

	@classmethod
	def remove (cls, node):
		parent = node.getparent()
		if parent is not None:
			if node.tail:
				prev = node.getprevious()
				if prev is None:
					if not parent.text:
						parent.text = ''
					parent.text += u' ' + node.tail
				else:
					if not prev.tail:
						prev.tail = ''
					prev.tail += u' ' + node.tail
			node.clear()
			parent.remove(node)

	@classmethod
	def get_tag (cls, node):
		return node.tag

	@classmethod
	def get_text (cls, node):
		txts = [i for i in node.itertext()]		
		return innerTrim(u' '.join(txts).strip())
	
	@classmethod
	def get_text_nodes (cls, node, strip = True):
		if strip:
			return [i.strip () for i in node.itertext()]
		else:	
			return [i for i in node.itertext()]
			
	@classmethod
	def get_text_node_count (cls, node):
		txts = filter (None, [i.strip () for i in node.itertext()])
		return len (txts)

	@classmethod
	def previous_siblings (cls, node):
		nodes = []
		for c, n in enumerate (node.itersiblings(preceding=True)):
			nodes.append(n)
		return nodes
		
	@classmethod
	def previous_sibling (cls, node):
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
	def is_text_node (cls, node):
		return True if node.tag == 'text' else False

	@classmethod
	def outer_html (cls, node):
		e0 = node
		if e0.tail:
			e0 = deepcopy(e0)
			e0.tail = None
		return cls.node_to_string(e0)
	
	@classmethod
	def omit_tag (cls, doc, tag):
		tbodies = cls.get_elements_by_tag(doc, tag)
		for tbody in tbodies:
			p = tbody.getparent ()
			for child in tbody.getchildren ():
				p.append(child)
			p.remove (tbody)
	
	@classmethod	
	def remove_tag (cls, doc, tag):
		nodes = cls.get_elements_by_tag(doc, tag)
		for node in nodes:
			cls.remove(node)			
	
	@classmethod
	def drop_tag (cls, nodes):
		if isinstance(nodes, list):
			for node in nodes:
				node.drop_tag()
		else:
			nodes.drop_tag()
	
	@classmethod
	def get_attribute (cls, node, attr=None):
		if attr:
			return node.attrib.get(attr, None)
		return attr
	
	@classmethod
	def has_attribute (cls, node):
		return len (node.attrib)
		
	@classmethod
	def del_attribute (cls, node, attr=None):
		if attr:
			_attr = node.attrib.get(attr, None)
			if _attr:
				del node.attrib[attr]

	@classmethod
	def set_attribute (cls, node, attr=None, value=None):
		if attr and value:
			node.set(attr, value)
				

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

