import os
import re
from . import utils
from .import sql
from .q import Q, generate_filters

class SQLGen:
	def __init__ (self, map = None, auto_reload = False):
		self._map = map
		self._auto_reload = auto_reload
		self._sqls = {}
		self._last_modifed = 0		
		if self._map:
			self._read_from_file ()
	
	def __getattr__ (self, name):		
		self._reloaderble () and self._read_from_file ()
		return sql.SQL (self._sqls.get (name))
		
	def _reloaderble (self):
		return self._map and self._auto_reload and self._last_modifed != os.path.getmtime (self._map)
		
	def _read_from_file (self):
		self._last_modifed = os.path.getmtime (self._map)
		with open (self._map) as f:
			self._read_from_string (f.read ())
	
	RX_NAME	= re.compile ("\sname\s*=\s*['\"](.+?)['\"]")
	def _read_from_string (self, data):
		current_name = None
		current_data = []
		for line in data.split ("\n"):
			line = line.strip ()
			if not line:
				continue
			
			if line.startswith ("</sql>"):
				if not current_name:
					raise ValueError ("unexpected end tag </sql>")
				self._sqls [current_name] = "\n".join (current_data)
				current_name, current_data = None, []				 
			
			elif line.startswith ("<sql "):
				m = self.RX_NAME.search (line)
				if not m:
					raise ValueError ("name attribute required")
				current_name = m.group (1)
			
			elif current_name:
				current_data.append (line)		


class Operation:
	def insert (self, tbl, fields = None):
		assert isinstance (fields, dict)
		return sql.SQL2 (utils.make_insert_statement (tbl, fields))
	
	def update (self, tbl, fields = None):
		assert isinstance (fields, dict)
		return sql.SQL2 (utils.make_update_statement (tbl, fields))		
	
	def select (self, tbl, fields = ["*"]):
		assert isinstance (fields, (list, tuple))
		return sql.SQL2 (utils.make_select_statement (tbl, fields))		
	
	def delete (self, tbl):
		return sql.SQL2 (utils.make_delete_statement (tbl))

		
class SQLLoader:
	def __init__ (self, dir = None, auto_reload = False):
		self._dir = dir
		self._auto_reload = auto_reload
		self.ops = Operation ()
		self._ns = {}
		self._load_sqlmaps ()
		
	def __getattr__ (self, name):
		try:
			return self._ns [name]
		except KeyError:
			return getattr (self._ns ["default"], name)
		
	def _load_sqlmaps (self):	
		for fn in os.listdir (self._dir):
			if fn[0] == "#":
				continue			
			ns = fn.split (".") [0]
			if ns == "ops":
				raise NameError ('ops cannot be used SQL map file name')
			self._ns [ns] = SQLGen (os.path.join (self._dir, fn), self._auto_reload)
	