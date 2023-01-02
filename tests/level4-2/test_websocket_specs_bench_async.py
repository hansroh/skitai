from websockets import connect
import time
import pytest
import asyncio

N = 1000
CLIENTS = 3
DUE = []

async def bench (ep):
    global DUE
    async with connect (f"ws://127.0.0.1:30371/websocket/bench/{ep}") as ws:
        s = time.time ()
        for _ in range (N):
            await ws.send("Hello, World")
            result = await ws.recv()
            assert result == "echo: Hello, World"
        DUE.append (time.time () - s)

async def clients (launch, ep):
    with launch ("./examples/websocket-spec.py") as engine:
        try:
            asyncio.create_task
        except AttributeError:
            await asyncio.wait ([bench (ep) for _ in range (CLIENTS)])
        else:
            await asyncio.wait ([asyncio.create_task (bench (ep)) for _ in range (CLIENTS)])
        assert int (engine.get ("/websocket/bench/N").text) in (N * CLIENTS, N * CLIENTS + CLIENTS)
        print ('*********** Bench result: {} {:2.3f}'.format (ep, sum (DUE)))

@pytest.mark.asyncio
async def test_bench2 (launch):
    await clients (launch, 'chatty')

@pytest.mark.asyncio
async def test_bench3 (launch):
    await clients (launch, 'session')

@pytest.mark.asyncio
async def test_bench4 (launch):
    await clients (launch, 'async')

@pytest.mark.asyncio
async def test_bench6 (launch):
    await clients (launch, 'session_nopool')

@pytest.mark.asyncio
async def test_bench7 (launch):
    await clients (launch, 'async_channel')
