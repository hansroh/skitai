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
	def __init__ (self, *args, **kargs):
		self._str = None		
		if kargs:
			assert len (kargs) == 1
			self.k, self.v = kargs.popitem ()
		elif len (args) == 2:
			self.k, self.v = args
		else:	
			self._str = args [0]
	
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
		return Q ("(({}) OR ({}))".format (self, b))
	
	def __and__ (self, b):
		return Q ("(({}) AND ({}))".format (self, b))	


def batch (**filters):
	Qs = []
	for k, v in filters.items ():
		Qs.append (Q (k, v))
	return Qs
	