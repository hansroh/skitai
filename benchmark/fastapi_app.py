# uvicorn app_fastapi:app --host 0.0.0.0 --port 9007 --workers 2

from fastapi import FastAPI
import asyncpg
import asyncio
import os

app = FastAPI()
pool = None
@app.on_event("startup")
async def startup():
    global pool
    auth, netloc = os.environ ['MYDB'].split ("@")
    user, passwd = auth.split (":")
    host, database = netloc.split ("/")
    pool = await asyncpg.create_pool (user=user, password=passwd, database=database, host=host)

@app.get("/bench")
async def bench():
    async def query (q):
        async with pool.acquire() as conn:
            return await conn.fetch (q)

    values, record_count = await asyncio.gather (
        query ('''SELECT * FROM foo where from_wallet_id=8 or detail = 'ReturnTx' order by created_at desc limit 10;'''),
        query ('''SELECT count (*) as cnt FROM foo where from_wallet_id=8 or detail = 'ReturnTx';''')
    )
    return {"txn": values, 'record_count': record_count [0]['cnt']}
