from rs4 import asyncore
import time

def _make (was, flt):
	g = {}

	if flt:
		if flt == "ENVIRON":
			return {"ENVIRON": was.env}

	for attr in dir (was):
		if attr.startswith ("__") or attr == "config": continue
		if flt and flt != attr.upper (): continue
		obj = eval ("was." + attr)
		if hasattr (obj, "status"):
			g [attr.upper ()] = obj.status ()

	return g


def format_object (o, depth = 0):
	b = []
	if type (o) in (type ([]), type (())):
		for each in o:
			if type (each) is type ({}):
				b.append ("%s" % format_object (each, depth + 1))
			elif type (each) is type ([]):
				b.append (", ".join ([str (x) for x in each]))
			else:
				if not b:
					b.append ("<ul>")
				b.append ("<li>%s</li>" % str (each))
		if b and b [0] == "<ul>":
			b.append ("</ul>")
		return "".join (b)

	b.append ("<table width='100%' border='0'>")
	ii = list(o.items ())
	ii.sort ()
	width = 18 + (depth * 6)
	for idx, (k1, v1) in enumerate (ii):
		if isinstance (v1, (list, dict)):
			b.append ("<tr><td bgcolor='#C8EFD4' valign='top' width='%d%%' style='word-break: break-all; padding: 6px;'><b>%s%s</b></td>" % (width, str (k1), type (v1) in (list, tuple) and " (%d)" % (len (v1),) or ""))
			b.append ("<td valign='top' style='padding: 0;'>%s</td></tr>" % format_object (v1, depth + 1))
		else:
			if depth > 0 and idx == 0:
				b.append ("<tr><td valign='top' colspan='2' style='padding: 6; color: #888; font-size: 11px;'><b>Object</b></td></tr>")
			b.append ("<tr><td bgcolor='#98E0AD' valign='top' width='%d%%' style='word-break: break-all; padding: 6px;'><b>%s</b></td>" % (width, str (k1)))
			b.append ("<td valign='top' style='word-break: break-all; padding: 6px;'>%s</td></tr>" % str (v1))
	b.append ("</table>")
	return "".join (b)


def formatting (was, info, flt):
	b = [
		"<!DOCTYPE html>"
		"<html><head>"
		"<title>Skitai App Engine Status</title>"
		"</head><body style='font-size: 12px;''>"
	]
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
			b.append ("<a name='%s'></a><h3><a href='%s?f=%s'>%s</a></h3>" % (k, was.request.split_uri ()[0], k, k))
		else:
			b.append ("<h3><a href='%s'>%s</a></h3>" % (was.request.split_uri ()[0], k))

		b.append (format_object (v))
		if not flt:
			b.append ('<div style="margin-bottom: 30px; padding: 5px;"><a href="#TOC">TOC</a></div>')
		else:
			b.append ('<div style="margin-bottom: 30px; padding: 5px;"><a href="%s">TOC</a></div>' % was.request.split_uri ()[0])
	b.append ("</body></html>")
	return "".join (b)


def make (was, flt = None, fancy = True):
	info = _make (was, flt)
	if fancy:
		return formatting (was, info, flt)
	return info
