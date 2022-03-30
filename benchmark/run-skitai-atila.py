#!/usr/bin/env python3

from atila import Atila
from sqlphile import Q
import time
from skitai import was
from sqlphile import pg2
import json
import random
app = Atila (__name__)

SLEEP = 0.3
pool = pg2.Pool (200, "skitai", "skitai", "12345678")

@app.route ("/status")
def status (was, f = None):
    return was.status (f)


# official ---------------------------------------------
@app.route ("/bench", methods = ['GET'])
def bench (was):
    with pool.acquire () as db:
        txs = db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;''').fetch ()
        record_count = db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''').one () ["cnt"]
        return was.API (
            txs = txs,
            record_count = record_count
        )

@app.route ("/bench/mix", methods = ['GET'])
def bench_mix (was):
    was.Thread (time.sleep, args = (SLEEP,))
    with pool.acquire () as db:
        txs = db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;''').fetch ()
        record_count = db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''').one () ["cnt"]
        return was.API (
            txs = txs,
            record_count = record_count
        )

# pilots ------------------------------------------------
@app.route ("/bench/sp", methods = ['GET'])
def bench_sp (was):
    with pool.acquire () as db:
        q = (db.select ("foo")
                    .filter (Q (from_wallet_id = 8) | Q (detail = 'ReturnTx'))
                    .order_by ("-created_at")
                    .limit (10)
        )
        return was.API (
            txs = q.execute ().fetch (),
            record_count = q.aggregate ('count (id) as cnt').execute ().one () ["cnt"]
        )

@app.route ("/bench/long", methods = ['GET'])
@app.inspect (floats = ['t'])
def bench_long (was, t = 1.0):
    time.sleep (t)
    return was.API ()

@app.route ("/bench/one", methods = ['GET'])
def bench_one (was):
    with pool.acquire () as db:
        return was.API (
            txs = db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;''').fetch ()
        )

@app.route ("/bench/http", methods = ['GET'])
def bench_http (was):
    return was.Map (
        t1 = was.get ('@myweb/', headers = {'Accept': 'text/html'}),
    )

@app.route ("/bench/http/2", methods = ['GET'])
def bench_http2 (was):
    return was.Map (
        t1 =  was.get ('@myweb/', headers = {'Accept': 'text/html'}),
        t2 =  was.get ('@myweb/', headers = {'Accept': 'text/html'}),
    )

if __name__ == '__main__':
    import skitai, os

    skitai.alias ('@myweb', skitai.PROTO_HTTPS, 'example.com', max_conns = 32)
    skitai.mount ('/', app)
    skitai.use_poll ('epoll')
    skitai.run (workers = 4, threads = 4, port = 5000)
