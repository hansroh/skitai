#!/usr/bin/env python3

from atila import Atila
from sqlphile import Q
import time
from skitai import was
import json

app = Atila (__name__)


@app.route ("/bench", methods = ['GET'])
def bench2 (was):
    with was.db ('@mydb') as db:
        ts = was.Tasks (
            db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;'''),
            db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''')
        )
    txs, aggr = ts.fetch ()
    return was.API (txs =  txs, record_count = aggr [0].cnt)

@app.route ("/bench/mix", methods = ['GET'])
def bench_mix (was):
    def response (was, txs, aggr):
        time.sleep (0.1)
        return was.API (txs = txs, record_count = aggr [0].cnt)

    with was.db ('@mydb') as db:
        ts = was.Tasks (
            db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;'''),
            db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''')
        )
        txs, aggr = ts.fetch ()
    return was.ThreadFuture (response, args = (txs, aggr))

@app.route ("/bench/mix/2", methods = ['GET'])
def bench_mix2 (was):
    def response (was, tasks):
        txs, aggr, _ = tasks.fetch ()
        return was.API (txs = txs, record_count = aggr [0].cnt)

    with was.db ('@mydb') as db:
        ts = was.Tasks (
            db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;'''),
            db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';'''),
            was.Thread (time.sleep, args = (0.1,))
        )
    return ts.then (response)

@app.route ("/bench/sp", methods = ['GET'])
def bench (was):
    with was.db ('@mydb') as db:
        root = (db.select ("foo")
                    .order_by ("-created_at")
                    .limit (10)
                    .filter (Q (from_wallet_id = 8) | Q (detail = 'ReturnTx')))
        txs, aggr = was.Tasks (
            root.execute (),
            root.clone ().aggregate ('count (id) as cnt').execute ()
        ).fetch ()

    return was.API (
        txs =  txs,
        record_count = aggr [0].cnt
    )

if __name__ == '__main__':
    import skitai, os

    skitai.alias ('@mydb', skitai.DB_PGSQL, os.environ ['MYDB'])
    skitai.mount ('/', app)
    skitai.run (workers = 4, threads = 4, port = 9007)
