from . import utils
from .q import Q, generate_filters

class SQL:
	def __init__ (self, template):	
		self._template = template		
		self._filters = []
		self._limit = 0
		self._offset = 0
		self._order_by = None
		self._group_by = None
		self._feed = {}
	
	@property
	def query (self):
		return self.as_sql ()
	
	def filter (self, *Qs, **filters):
		for q in Qs:
			self._filters.append (str (q))
		self._filters.append (generate_filters (**filters))
		return self
	
	def order_by (self, *by):
		self._order_by = utils.make_orders (by)
		return self
	
	def group_by (self, *by):
		self._group_by = utils.make_orders (by, "GROUP")
		return self
		
	def limit (self, val):
		self._limit = "LIMIT {}".format (val)
		return self
	
	def offset (self, val):
		self._offset = "OFFSET {}".format (val)
		return self
	
	def feed (self, **karg):		
		for k, v in karg.items ():
			self._feed [k] = v
		return self
	
	def as_sql (self):
		return self._template.format (
			filters = " AND ".join (self._filters),
			limit = self._limit,
			offset = self._offset,
			order_by = self._order_by,
			group_by = self._group_by,
			**self._feed
		)
	

class SQL2 (SQL):	
	def as_sql (self):
		sql = [self._template]
		self._filters and sql.append ("WHERE " + " AND ".join (self._filters))
		self._group_by and sql.append (self._group_by)
		self._order_by and sql.append (self._order_by)
		self._limit and sql.append (self._limit)
		self._offset and sql.append (self._offset)
		return "\n".join (sql)
