from websocket import create_connection

def test_websocket_coroutine (launch):
    with launch ("./examples/websocket-spec.py") as engine:
        ws = create_connection("ws://127.0.0.1:30371/websocket/coroutine")
        ws.send("Hello, World")
        result =  ws.recv()
        assert result == "echo: Hello, World"

        ws.send("Hello, World")
        ws.send("Hello, World")
        result =  ws.recv()
        assert result == "echo: Hello, World"
        result =  ws.recv()
        assert result == "echo: Hello, World"
        result =  ws.recv()
        assert result == "double echo: Hello, World"
        ws.close()


def test_websocket_chatty (launch):
    with launch ("./examples/websocket-spec.py") as engine:
        ws = create_connection("ws://127.0.0.1:30371/websocket/chatty")
        ws.send("Hello, World")
        result =  ws.recv()
        assert result == "1st: Hello, World"

        ws.send("Hello, World")
        result =  ws.recv()
        assert result == "pre2nd: Hello, World"
        result =  ws.recv()
        assert result == "2nd: Hello, World"
        result =  ws.recv()
        assert result == "post2nd: Hello, World"

        ws.send("Hello, World")
        result =  ws.recv()
        assert result == "many: Hello, World"

        ws.close()

def test_websocket_reporty (launch):
    with launch ("./examples/websocket-spec.py") as engine:
        ws = create_connection("ws://127.0.0.1:30371/websocket/reporty?a=AMBER")
        ws.send("Hello, World")

        result =  ws.recv()
        assert result == "hi"

        result =  ws.recv()
        assert result == "first message"

        result =  ws.recv()
        assert result == "AMBER: Hello, World"

        ws.send("Hello, World2")

        result =  ws.recv()
        assert result == "first message"

        result =  ws.recv()
        assert result == "AMBER: Hello, World2"

        ws.close()

def test_websocket_reporty_async (launch, launch_dry):
    with launch ("./examples/websocket-spec.py") as engine:
        ws = create_connection("ws://127.0.0.1:30371/websocket/reporty/async?a=AMBER")
        ws.send("Hello, World")

        result =  ws.recv()
        assert result == "hi"

        result =  ws.recv()
        assert result == "first message"

        result =  ws.recv()
        assert result == "AMBER: Hello, World"

        ws.send("Hello, World2")

        result =  ws.recv()
        assert result == "first message"

        result =  ws.recv()
        assert result == "AMBER: Hello, World2"

        ws.close()
