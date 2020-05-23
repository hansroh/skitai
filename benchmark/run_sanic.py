#!/usr/bin/env python3

from sanic import Sanic
from sanic.response import json, HTTPResponse
import asyncpg
import asyncio
import os
from skitai.wastuff.api import decode_json

app = Sanic(__name__)

pool = None
@app.listener('before_server_start')
async def startup(app, loop):
    global pool
    auth, netloc = os.environ ['MYDB'].split ("@")
    user, passwd = auth.split (":")
    host, database = netloc.split ("/")
    pool = await asyncpg.create_pool (user=user, password=passwd, database=database, host=host)

@app.route("/bench")
async def bench(request):
    async def query (q):
        async with pool.acquire() as conn:
            return await conn.fetch (q)

    values, record_count = await asyncio.gather (
        query ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;'''),
        query ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''')
    )
    return HTTPResponse (decode_json ({"txn": [dict (v) for v in values], 'record_count': record_count [0]['cnt']}))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9007, access_log=True, workers = 2)

