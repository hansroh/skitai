from . import utils

OPS = {
	"gt": ">",
	"gte": ">=",
	"lt": "<",
	"lte": "<=",
	"is": "IS",
	"isnot": "IS NOT",
	"neq": "<>",
	"eq": "=",
	"in": "IN",
	"notin": "NOT IN",
	"exists": "EXISTS",
	"nexists": "NOT EXISTS",
	"between": "BETWEEN",
	"contains": "LIKE",
	"startswith": "LIKE",
	"endswith": "LIKE",
	"ncontains": "NOT LIKE",
	"nstartswith": "NOT LIKE",
	"nendswith": "NOT LIKE",
}

class Q:
	def __init__ (self, k, v, _str = None):
		self.k = k
		self.v = v
		self._str = _str
	
	def render (self):
		if self._str:
			return self._str
		
		k, v = self.k, self.v
		
		try:
			fd, op = k.split ("__", 1)
		except ValueError:
			fd, op = k, "eq"
		
		if v is None:
			if op == "eq":
				op = "is"
				
		try:
			_op = OPS [op]
		except KeyError:
			raise TypeError ('Unknown Operator: {}'.format (op))
			
		_val = v
		if op.endswith ("contains"):
			_val = "%" + _val.replace ("%", "\\%") + "%"
		elif op.endswith ("startswith"):
			_val = _val.replace ("%", "\\%") + "%"	
		elif op.endswith ("endswith"):
			_val = "%" + _val.replace ("%", "\\%")
		elif op == "between":
			_val = "{} AND {}".format (*tuple (_val))		
		return "{} {} {}".format (fd, _op, utils.toval (_val))
		
	def __str__ (self):
		return self.render ()
	
	def __or__ (self, b):
		return Q (None, None, _str = "(({}) OR ({}))".format (self, b))
	
	def __and__ (self, b):
		return Q (None, None, _str = "(({}) AND ({}))".format (self, b))	


def generate_filters (**filters):
	fts = []
	for k, v in filters.items ():
		fts.append (str (Q (k, v)))
	return " AND ".join (fts)

def generate_filters (**filters):
	fts = []
	for k, v in filters.items ():
		fts.append (str (Q (k, v)))
	return " AND ".join (fts)
	