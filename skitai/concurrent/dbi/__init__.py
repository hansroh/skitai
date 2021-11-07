DB_PGSQL = "*postgresql"
DB_SYN_PGSQL = "*postgresql_syn"
DB_POSTGRESQL = "*postgresql"
DB_SQLITE3 = "*sqlite3"
DB_REDIS = "*redis"
DB_MONGODB = "*mongodb"
DB_SYN_REDIS = "*redis_syn"
DB_SYN_MONGODB = "*mongodb_syn"
DB_SYN_ORACLE = DB_ORACLE = "*oracle"

def set_timeout (timeout):
	# IMP: for preventing recursive import
	from rs4.protocols.dbi import asynmongo, asynpsycopg2, asynredis

	for each in (asynmongo.AsynConnect, asynpsycopg2.AsynConnect, asynredis.AsynConnect):
		each.zombie_timeout = timeout
