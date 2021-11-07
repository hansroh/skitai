from . import asynconnect
from rs4.protocols.dbi import asynmongo, asynpsycopg2, asynredis

def set_timeout (timeout):
	for each in (asynconnect.AsynConnect, asynconnect.AsynSSLConnect, asynconnect.AsynSSLProxyConnect):
		each.keep_alive = timeout
		each.zombie_timeout = timeout

	for each in (asynmongo.AsynConnect, asynpsycopg2.AsynConnect, asynredis.AsynConnect):
		each.zombie_timeout = timeout
