#!/usr/bin/env python3

from atila import Atila
from sqlphile import Q
import time
from sqlphile import pg2
import asyncpg
import asyncio
import os
from atila.collabo import requests

TARGET = "example.com" if os.getenv ("GITLAB_CI") else "192.168.0.154:5500"

app = Atila (__name__, __file__)

async def __setup__ (context):
    auth, netloc = os.environ ['MYDB'].split ("@")
    user, passwd = auth.split (":")
    host, database = netloc.split ("/")
    context.app.rpool = requests.Pool (200)
    context.app.spool = pg2.Pool (200, user, database, passwd, host)
    if not os.getenv ("GITLAB_CI"): # Permission denied: '/root/.postgresql/postgresql.key
        context.app.apool = await asyncpg.create_pool (user=user, password=passwd, database=database, host=host, min_size=1, max_size=20)

async def __umounted__ (context):
    context.app.spool.close ()
    if not os.getenv ("GITLAB_CI"):
        await context.app.apool.close ()


@app.route ("/status")
def status (context, f = None):
    return context.status (f)

# official ---------------------------------------------
@app.route ("/bench", methods = ['GET'])
def bench (context):
    with app.spool.acquire () as db:
        txs = db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;''').fetch ()
        record_count = db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''').one () ["cnt"]
        return context.API (
            txs = txs,
            record_count = record_count
        )

@app.route ("/bench/async", methods = ['GET'])
async def query_async (context):
    async def query (q):
        async with app.apool.acquire () as conn:
            return await conn.fetch (q)

    if os.getenv ("GITLAB_CI"):
        return context.API (txs = [], record_count = 1000)
    values, record_count = await asyncio.gather (
        query ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;'''),
        query ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''')
    )
    return context.API (txs = [dict(r.items()) for r in values], record_count = record_count [0]['cnt'])

@app.route ("/bench/sqlphile", methods = ['GET'])
def bench_sp (context):
    with app.spool.acquire () as db:
        q = (db.select ("foo")
                    .filter (Q (from_wallet_id = 8) | Q (detail = 'ReturnTx'))
                    .order_by ("-created_at")
                    .limit (10)
        )
        return context.API (
            txs = q.execute ().fetch (),
            record_count = q.aggregate ('count (id) as cnt').execute ().one () ["cnt"]
        )

@app.route ("/bench/delay", methods = ['GET'])
@app.spec (floats = ['t'])
def bench_delay (context, t = 0.3):
    task = context.Thread (time.sleep, args = (t,))
    with app.spool.acquire () as db:
        txs = db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;''').fetch ()
        record_count = db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''').one () ["cnt"]
        return context.API (
            tasl = task.fetch (),
            txs = txs,
            record_count = record_count
        )

@app.route ("/bench/http", methods = ['GET'])
def bench_http_requests (context):
    with app.rpool.acquire () as s:
        return context.API (
            t1 = s.get (f'http://{TARGET}', headers = {'Accept': 'text/html'}).text
        )


if __name__ == '__main__':
    import skitai, os

    skitai.mount ('/', app)
    skitai.use_poll ('epoll')
    skitai.enable_async (20)
    skitai.set_503_estimated_timeout (0)
    skitai.run (workers = 4, threads = 4, port = 5000)
