#!/usr/bin/env python3

from atila import Atila
from sqlphile import Q
import time
from skitai import was
import json

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
            record_count__cnt = db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''')
        )

@app.route ("/bench/mix", methods = ['GET'])
def bench_mix (was):
    with was.db ('@mydb') as db:
        return was.Map (
            was.Thread (time.sleep, args = (SLEEP,)),
            txs = db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;'''),
            record_count__cnt = db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''')
        )


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
            record_count__cnt = q.aggregate ('count (id) as cnt').execute ()
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
    return was.ThreadFuture (response, args = (txs, aggr))


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
    return was.Map (txs =  was.get ('@myweb/apis/settings'))


if __name__ == '__main__':
    import skitai, os

    skitai.alias ('@mydb', skitai.DB_PGSQL, os.environ ['MYDB'], max_conns = 16)
    skitai.alias ('@myweb', skitai.PROTO_HTTP, '192.168.0.154:9019', max_conns = 16)
    skitai.mount ('/', app)
    skitai.run (workers = 4, threads = 4, port = 9007)
