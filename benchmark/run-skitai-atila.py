#!/usr/bin/env python3

from atila import Atila
from sqlphile import Q
import time
from skitai import was
import json
import random
app = Atila (__name__)

SLEEP = 0.3

@app.route ("/status")
def status (was, f = None):
    return was.status (f)


# official ---------------------------------------------
@app.route ("/bench", methods = ['GET'])
def bench (was):
    with was.db ('@mydb') as db:
        return was.Map (
            txs = db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;'''),
            record_count__one__cnt = db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''')
        )

@app.route ("/bench/mix", methods = ['GET'])
def bench_mix (was):
    with was.db ('@mydb') as db:
        return was.Map (
            was.Thread (time.sleep, args = (SLEEP,)),
            txs = db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;'''),
            record_count__one__cnt = db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''')
        )

@app.route ("/bench/row", methods = ['GET'], coroutine = True)
def bench_row (was, pre = None):
    with was.db ('@mydb') as db:
        if pre:
            yield db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;''')
        return was.Map (
            txs = db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 1;''')
        )

@app.route ("/bench/gen", methods = ['GET'], coroutine = True)
@app.inspect (ints = ['n'])
def bench_gen (was, n = 100):
    with was.db ('@mydb') as db:
        last_id = random.randrange (100000, 101000)
        while 1:
            task = yield db.execute ('''SELECT * FROM foo where detail = 'ReturnTx' and id > {} order by id desc limit 100;'''.format (last_id))
            n -= 1
            if n == 0:
                break
            rows = task.fetch ()
            if not rows:
                last_id = random.randrange (100000, 101000)
                continue
            last_id = rows [-1].id
            yield str (rows)

# pilots ------------------------------------------------
@app.route ("/bench/sp", methods = ['GET'])
def bench_sp (was):
    with was.db ('@mydb') as db:
        q = (db.select ("foo")
                    .filter (Q (from_wallet_id = 8) | Q (detail = 'ReturnTx'))
                    .order_by ("-created_at")
                    .limit (10)
        )
        return was.Map (
            txs = q.execute (),
            record_count__one__cnt = q.aggregate ('count (id) as cnt').execute ()
        )


@app.route ("/bench/2", methods = ['GET'])
def bench2 (was):
    with was.db ('@mydb') as db:
        ts = was.Tasks (
            db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;'''),
            db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''')
        )
    txs, aggr = ts.fetch ()
    return was.API (
        txs =  txs,
        record_count = aggr [0].cnt
    )

@app.route ("/bench/mix/2", methods = ['GET'])
def bench_mix1 (was):
    def response (was, txs, aggr):
        time.sleep (SLEEP)
        return was.API (txs = txs, record_count = aggr [0].cnt)

    with was.db ('@mydb') as db:
        ts = was.Tasks (
            db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;'''),
            db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''')
        )
        txs, aggr = ts.fetch ()
    return was.ThreadPass (response, args = (txs, aggr))

@app.route ("/bench/long", methods = ['GET'])
@app.inspect (floats = ['t'])
def bench_long (was, t = 1.0):
    time.sleep (t)
    return was.API ()

@app.route ("/bench/one", methods = ['GET'])
def bench_one (was):
    with was.db ('@mydb') as db:
        return was.Map (
            txs = db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;''')
        )

@app.route ("/bench/one/2", methods = ['GET'])
def bench_one2 (was):
    with was.db ('@mydb') as db:
        return was.API (
            txs = db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;''').fetch ()
        )


@app.route ("/bench/http", methods = ['GET'])
def bench_http (was):
    return was.Map (
        t1 = was.get ('@myweb/apis/settings/appDownloadUrl'),
    )

@app.route ("/bench/http/2", methods = ['GET'])
def bench_http2 (was):
    return was.Map (
        t1 =  was.get ('@myweb/status?f=ENVIRON', headers = {'Accept': 'text/html'}),
        t2 =  was.get ('@myweb/status?f=THREADS', headers = {'Accept': 'text/html'}),
    )


if __name__ == '__main__':
    import skitai, os

    skitai.alias ('@mydb', skitai.DB_PGSQL, os.environ ['MYDB'], max_conns = 10)
    skitai.alias ('@myweb', skitai.PROTO_HTTP, '192.168.0.154:9020', max_conns = 32)
    skitai.mount ('/', app)
    skitai.use_poll ('epoll')
    skitai.run (workers = 4, threads = 4, port = 9007)
