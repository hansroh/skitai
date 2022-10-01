# uvicorn app_fastapi:app --host 0.0.0.0 --port 9007 --workers 2

from fastapi import FastAPI
import asyncpg
import asyncio
import os
from sqlphile import pg2
from anyio.lowlevel import RunVar
from anyio import CapacityLimiter

app = FastAPI()
pool = None
spool = None

@app.on_event("startup")
async def startup():
    global pool, spool
    auth, netloc = os.environ ['MYDB'].split ("@")
    user, passwd = auth.split (":")
    host, database = netloc.split ("/")
    pool = await asyncpg.create_pool (user=user, password=passwd, database=database, host=host)
    spool = pg2.Pool (200, user, database, passwd, host)
    RunVar("_default_thread_limiter").set(CapacityLimiter(8))

@app.get("/bench")
def bench():
    with spool.acquire () as db:
        txs = db.execute ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;''').fetch ()
        record_count = db.execute ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''').one () ["cnt"]
        return dict (
            txs = txs,
            record_count = record_count
        )

@app.get("/bench/async")
async def bench_async():
    async def query (q):
        async with pool.acquire() as conn:
            return await conn.fetch (q)

    values, record_count = await asyncio.gather (
        query ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;'''),
        query ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''')
    )
    return {"txn": values, 'record_count': record_count [0]['cnt']}
