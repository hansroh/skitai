#!/usr/bin/env python3

from atila import Atila
from sqlphile import Q
import time
from sqlphile import pg2
import asyncpg
import asyncio
import os
from atila.collabo import requests

TARGET = "example.com" if os.getenv ("GITLAB_CI") else "192.168.0.154:6001"

app = Atila (__name__, __file__)

async def __setup__ (app, mntopt):
    app.rpool = requests.Pool (200)
    app.spool = pg2.Pool (200, "skitai", "skitai", "12345678")
    if not os.getenv ("GITLAB_CI"): # Permission denied: '/root/.postgresql/postgresql.key
        app.apool = await asyncpg.create_pool (user='skitai', password='12345678', database='skitai', host='127.0.0.1', min_size=1, max_size=20)

async def __umounted__ (app):
    app.spool.close ()
    if not os.getenv ("GITLAB_CI"):
        await app.apool.close ()


@app.route ("/status")
def status (was, f = None):
    return was.status (f)

# official ---------------------------------------------
@app.route ("/bench", methods = ['GET'])
def bench (was):
    with app.spool.acquire () as db:
        txs = db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;''').fetch ()
        record_count = db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''').one () ["cnt"]
        return was.API (
            txs = txs,
            record_count = record_count
        )

@app.route ("/bench/async", methods = ['GET'])
async def query_async (was):
    async def query (q):
        async with app.apool.acquire () as conn:
            return await conn.fetch (q)

    if os.getenv ("GITLAB_CI"):
        return was.API (txs = [], record_count = 1000)
    values, record_count = await asyncio.gather (
        query ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;'''),
        query ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''')
    )
    return was.API (txs = [dict(r.items()) for r in values], record_count = record_count [0]['cnt'])

@app.route ("/bench/sqlphile", methods = ['GET'])
def bench_sp (was):
    with app.spool.acquire () as db:
        q = (db.select ("foo")
                    .filter (Q (from_wallet_id = 8) | Q (detail = 'ReturnTx'))
                    .order_by ("-created_at")
                    .limit (10)
        )
        return was.API (
            txs = q.execute ().fetch (),
            record_count = q.aggregate ('count (id) as cnt').execute ().one () ["cnt"]
        )

@app.route ("/bench/delay", methods = ['GET'])
@app.spec (floats = ['t'])
def bench_delay (was, t = 0.3):
    task = was.Thread (time.sleep, args = (t,))
    with app.spool.acquire () as db:
        txs = db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;''').fetch ()
        record_count = db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''').one () ["cnt"]
        return was.API (
            tasl = task.fetch (),
            txs = txs,
            record_count = record_count
        )

@app.route ("/bench/http", methods = ['GET'])
def bench_http_requests (was):
    with app.rpool.acquire () as s:
        return was.API (
            t1 = s.get (f'http://{TARGET}', headers = {'Accept': 'text/html'}).text
        )


if __name__ == '__main__':
    import skitai, os

    skitai.mount ('/', app)
    skitai.use_poll ('epoll')
    skitai.enable_async (20)
    skitai.set_503_estimated_timeout (0)
    skitai.run (workers = 4, threads = 4, port = 5000)
