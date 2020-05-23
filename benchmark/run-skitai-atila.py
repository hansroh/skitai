#!/usr/bin/env python3

from atila import Atila
from sqlphile import Q

app = Atila (__name__)

@app.route ("/bench", methods = ['GET'])
def bench2 (was):
    with was.db ('@mydb') as db:
        qs = [
            db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 30;'''),
            db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''')
        ]
        txs, aggr = was.Tasks (qs).fetch ()

    return was.API (
        txs =  txs,
        record_count = aggr [0].cnt
    )


@app.route ("/bench2", methods = ['GET'])
def bench (was):
    with was.db ('@mydb') as db:
        root = (db.select ("foo")
                    .order_by ("-created_at")
                    .limit (30)
                    .filter (Q (from_wallet_id = 8) | Q (detail = 'ReturnTx')))

        qs = [
            root.execute (),
            root.clone ().aggregate ('count (id) as cnt').execute ()
        ]
        txs, aggr = was.Tasks (qs).fetch ()

    return was.API (
        txs =  txs,
        record_count = aggr [0].cnt
    )

if __name__ == '__main__':
    import skitai, os

    skitai.alias ('@mydb', skitai.DB_PGSQL, os.environ ['MYDB'])
    skitai.mount ('/', app)
    skitai.run (workers = 4, threads = 4, port = 9007)
