import pytest
from examples.services import route_guide_pb2
import os
import time
from websocket import create_connection

# @pytest.mark.skip
def test_grpc_request_bistream (launch):
    # if os.getenv ("GITLAB_USER_NAME"):
    #     return
    try: import grpc
    except ImportError: return

    def make_route_note(message, latitude, longitude):
        return route_guide_pb2.RouteNote(
            message=message,
            location=route_guide_pb2.Point(latitude=latitude, longitude=longitude))

    def generate_messages():
        messages = [
            make_route_note("First message", 0, 0),
            make_route_note("Second message", 0, 1),
            make_route_note("Third message", 1, 0),
            make_route_note("Fourth message", 0, 0),
            make_route_note("Fifth message", 1, 0),
        ] * 3
        for i, msg in enumerate (messages):
            print ('send', i)
            time.sleep (1.0)
            yield msg

    server = "127.0.0.1:30371"
    with launch ("./examples/bidirectional.py") as engine:
        with grpc.insecure_channel(server) as channel:
            stub = route_guide_pb2.RouteGuideStub (channel)

            # bidirectional
            for idx, response in enumerate (stub.RouteChat(generate_messages())):
                print ('  - recv', idx)
                assert hasattr (response, 'message')
                assert hasattr (response, 'location')

            assert idx > 20


def test_websocket_coroutine (launch):
    with launch ("./examples/bidirectional.py") as engine:
        # test NOTHREAD ----------------------------------
        ws = create_connection("ws://127.0.0.1:30371/websocket")
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

def test_websocket_coroutine_thread (launch):
    with launch ("./examples/bidirectional.py") as engine:
        # test NOTHREAD ----------------------------------
        ws = create_connection("ws://127.0.0.1:30371/websocket/thread")
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

