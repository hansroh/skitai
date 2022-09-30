#!/usr/bin/env python3

from sanic import Sanic
from sanic.response import json, HTTPResponse
import asyncpg
import asyncio
import os
import time
from skitai.wastuff.api import tojson
import concurrent
import aiohttp
from sqlphile import pg2

app = Sanic(__name__)

SLEEP = 0.3

pool = None
spool = None
session = None
executor = concurrent.futures.ThreadPoolExecutor(max_workers = 4)

@app.listener('before_server_start')
async def startup(app, loop):
    global pool, session, spool
    auth, netloc = os.environ ['MYDB'].split ("@")
    user, passwd = auth.split (":")
    host, database = netloc.split ("/")
    pool = await asyncpg.create_pool (user=user, password=passwd, database=database, host=host, max_size = 10)
    _connector = aiohttp.connector.TCPConnector(limit = 32, limit_per_host = 32)
    session = await aiohttp.ClientSession(connector = _connector).__aenter__ ()
    spool = pg2.Pool (200, database, user, passwd)

async def query (q):
    async with pool.acquire() as conn:
        return await conn.fetch (q)

@app.route("/bench/async")
async def bench(request):
    values, record_count = await asyncio.gather (
        query ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;'''),
        query ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''')
    )
    return HTTPResponse (tojson ({"txn": [dict (v) for v in values], 'record_count': record_count [0]['cnt']}))

@app.route("/bench")
def bench(request):
    with spool.acquire () as db:
        txs = db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;''').fetch ()
        record_count = db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''').one () ["cnt"]
        return HTTPResponse (tojson (dict (
            txs = txs,
            record_count = record_count
        )))

@app.route("/bench/mix")
async def bench_mix(request):
    values, record_count, _ = await asyncio.gather (
        query ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;'''),
        query ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';'''),
        asyncio.get_event_loop ().run_in_executor (executor, time.sleep, SLEEP) # emulating blcokg job
    )
    return HTTPResponse (tojson ({"txn": [dict (v) for v in values], 'record_count': record_count [0]['cnt']}))

@app.route ("/bench/one", methods = ['GET'])
async def bench_mix3 (request):
    values = await query ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;''')
    return HTTPResponse (tojson ({"txn": [dict (v) for v in values]}))

@app.route ("/bench/row", methods = ['GET'])
async def bench_row (request):
    if request.query_args: # pref=1
        await query ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 1;''')
    values = await query ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 1;''')
    return HTTPResponse (tojson ({"txn": [dict (v) for v in values]}))

@app.route ("/bench/http", methods = ['GET'])
async def bench_http (request):
    async with session.get ("http://192.168.0.154:9019/apis/settings/appDownloadUrl", headers={"Accept": "application/json"}) as resp:
        text = await resp.read()
    return HTTPResponse (tojson ({"t1": text.decode ()}))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, access_log=True, workers = 4)

