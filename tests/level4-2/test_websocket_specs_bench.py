from websocket import create_connection
import time

N = 1000

def bench (launch, ep):
    with launch ("./examples/websocket-spec.py") as engine:
        ws = create_connection(f"ws://127.0.0.1:30371/websocket/bench/{ep}")
        s = time.time ()
        for _ in range (N):
            ws.send("Hello, World")
            result = ws.recv()
            assert result == "echo: Hello, World"
        ws.close()

        assert int (engine.get ("/websocket/bench/N").text) in (N, N + 1)
        print ('*********** Bench result: {} {:2.3f}'.format (ep, time.time () - s))

def test_bench2 (launch):
    bench (launch, 'chatty')

def test_bench4 (launch):
    bench (launch, 'async')

def test_bench3 (launch):
    bench (launch, 'session')

def test_bench6 (launch):
    bench (launch, 'session_nopool')

def test_bench7 (launch):
    bench (launch, 'async_channel')
