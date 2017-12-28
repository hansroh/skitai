from skitai.sqlgen import SQLGen, Operation, SQLLoader
import datetime
from skitai.sqlgen.q import Q

def test_Q ():	
	assert str (Q ("name", "Hans Roh")) == "name = 'Hans Roh'"
	assert str (Q ("name__startswith", "Hans Roh")) == "name LIKE 'Hans Roh%'"
	assert str (Q ("name__startswith", "Hans%20Roh")) == "name LIKE 'Hans\\%20Roh%'"
	assert str (Q ("name__nstartswith", "Hans%20Roh")) == "name NOT LIKE 'Hans\\%20Roh%'"
	assert str (Q ("name__neq", "Hans")) == "name <> 'Hans'"
	assert str (Q ("name", None)) == "name IS NULL"
	assert str (Q ("name__isnot", None)) == "name IS NOT NULL"
	assert str (Q ("a", 1) | Q ("b", 1) | Q ("c", 1)) == "((((a = 1) OR (b = 1))) OR (c = 1))"
	assert str (Q ("a", 1) & (Q ("b", 1) | Q ("c", 1))) == "((a = 1) AND (((b = 1) OR (c = 1))))"
	
def test_operation ():
	f = Operation ()
	sql = f.insert ("rc_file", {"_id": 1, "score": 1.3242, "name": "file-A", "moddate": datetime.date.today ()})
	sql = f.update ("rc_file", {"score": 1.3242, "name": "file-A", "moddate": datetime.date.today ()})
	sql.filter (_id = 1, name__contains = "Hans Roh").order_by ("name", "-type").group_by ("name")
	assert sql.query.find ("UPDATE rc_file SET") !=- 1
	assert sql.query.find ("score=1.3242") !=- 1
	assert sql.query.find ("WHERE") !=- 1
	assert sql.query.find ("GROUP BY name") !=- 1
	assert sql.query.find ("ORDER BY name, type DESC") !=- 1
	
def test_sqlgen ():	
	f = SQLGen ()
	f._read_from_string ("""
<sql name="test1">
	select * from {tbl} WHERE {filters} 
	{group_by}
	{order_by}	
</sql>	

<sql name="test2">
	select * from {tbl}	
</sql>
	""")
	assert len (f._sqls) == 2
	
	sql = f.test1
	sql = sql.filter (name = 'Hans').group_by ("name").order_by ("name").feed (tbl = 'rc_file')	
	
	assert sql.query == (
		"select * from rc_file WHERE name = 'Hans'\n"
		"GROUP BY name\n"
		"ORDER BY name"
	)

def test_SQLLoader ():
	map = SQLLoader ("sqlmaps")
	map.ops
	sql = map.test.test1.filter (name = 'Hans').group_by ("name").order_by ("name").feed (tbl = 'rc_file')	
	assert sql.query == (
		"select * from rc_file WHERE name = 'Hans'\n"
		"GROUP BY name\n"
		"ORDER BY name"
	)
	
	sql = map.test1.filter (name = 'Hans').group_by ("name").order_by ("name").feed (tbl = 'rc_file')	
	assert sql.query == (
		"select * from rc_file WHERE name = 'Hans'\n"
		"GROUP BY name\n"
		"ORDER BY name"
	)
	
	
	
	