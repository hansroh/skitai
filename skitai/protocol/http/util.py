import urllib

quote = urllib.quote_plus

def queryencode (data):
	if not data: return data
	if data.find ('%') > -1 or data.find ('+') > -1:
		return data

	d = []
	for x in data.split('&'):
		try: k, v = x.split('=', 1)
		except ValueError: d.append ((k, None))
		else:
			v = quote (v)
			d.append ((k, v))
	d2 = []
	for k, v in d:
		if v == None:
			d2.append (k)
		else:
			d2.append ('%s=%s' % (k, v))

	return '&'.join (d2)


def strparse (data, value_quote = 0):
	if not data: return []
	do_quote = 1
	if data.find('%') > -1 or data.find('+') > -1:
		do_quote = 0
	if not value_quote:
		do_quote = 0

	d = []
	for x in data.split(';'):
		try: k, v = x.split('=', 1)
		except ValueError: pass
		else:
			if do_quote:
				v = quote (v.strip())
			d.append((k.strip(), v.strip()))
	return d