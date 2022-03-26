from .impl import asynmongo, asynpsycopg2, asynredis

DB_POSTGRESQL = DB_PGSQL = "*postgresql"
DB_REDIS = "*redis"
DB_MONGODB = "*mongodb"
DB_SYN_PGSQL = "*postgresql_syn"
DB_SYN_REDIS = "*redis_syn"
DB_SYN_MONGODB = "*mongodb_syn"
DB_SYN_SQLITE3 = DB_SQLITE3 = "*sqlite3"
DB_SYN_ORACLE = DB_ORACLE = "*oracle"

def set_timeout (timeout):
	for each in (asynmongo.AsynConnect, asynpsycopg2.AsynConnect, asynredis.AsynConnect):
		each.zombie_timeout = timeout
