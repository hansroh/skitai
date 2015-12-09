import asyncore
import time

def _make (was, flt):
	g = {}
	
	if flt:
		if flt.startswith ("CLUSTER:"):
			return {flt: was.clusters [flt[8:]].status ()}
		elif flt == "SOCKETPOOL":
			return {flt: was.clusters [None].status ()}
		elif flt == "ENVIRON":
			return {"ENVIRON": was.env}	
	else:
		for name, cluster in list(was.clusters.items ()):
			if name is None: 
				g ["SOCKETPOOL"] = cluster.status ()
				continue
			g ["CLUSTER:" + name] = cluster.status ()
			g ["ENVIRON"] = was.env
			
	for attr in dir (was):
		if attr.startswith ("__") or attr == "config": continue
		if flt and flt != attr.upper (): continue
		obj = eval ("was." + attr)
		if hasattr (obj, "status"):			
			g [attr.upper ()] = obj.status ()
	
	return g
	
	
def format_object (o):
	b = []
	if type (o) in (type ([]), type (())):
		for each in o:
			b.append ("<div>")
			if type (each) is type ({}):
				b.append ("%s" % format_object (each))
			elif type (each) is type ([]):
				b.append (", ".join ([str (x) for x in each]))
			else:					
				b.append (str (each))	
			b.append ("</div>")				
		return "".join (b)

	b.append ("<table width='100%%' border='1'>")
	ii = list(o.items ())
	ii.sort ()
	
	for k1, v1 in ii:
		if type (v1) in (type ([]), type ({})):
			b.append ("<tr><td bgcolor='#efefef' valign='top'><b>%s%s</b></td>" % (str (k1), type (v1) is type ([]) and " (%d)" % (len (v1),) or ""))			
			b.append ("<td valign='top'>%s</td></tr>" % format_object (v1))			
		else:
			b.append ("<tr><td bgcolor='#efefef' valign='top'>%s</td>" % str (k1))			
			b.append ("<td valign='top'>%s</td></tr>" % str (v1))
	b.append ("</table>")	
	return "".join (b)

	
def formatting (was, info, flt):	
	b = []
	l = list(info.items ())
	l.sort ()
	if not flt:
		b.append ('<a name="TOC"></a><h3>Table of Content</h3>')
		b.append ('<ol>')
		for k, v in l:
			b.append ("<li><a href='#%s'>%s</a></li>" % (k, k))		
		b.append ('</ol>')
	
	for k, v in l:
		if not flt:
			b.append ("<a name='%s'></a><h3><a href='%s?f=%s'>%s</a></h3>" % (k, was.request.uri, k, k))
		else:
			b.append ("<h3><a href='%s'>%s</a></h3>" % (was.request.split_uri ()[0], k))	
			
		b.append (format_object (v))
		if not flt:
			b.append ('<div style="margin-bottom: 30px; padding: 5px;"><a href="#TOC">TOC</a></div>')
		else:
			b.append ('<div style="margin-bottom: 30px; padding: 5px;"><a href="%s">TOC</a></div>' % was.request.split_uri ()[0])
	return "".join (b)
	

def make (was, flt = None, fancy = True):
	info = _make (was, flt)
	if fancy:
		return formatting (was, info, flt)	
	return info

