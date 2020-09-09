import pytest
from xmlrpc.client import ProtocolError
def test_multiple_root_mounted (launch):
    with launch ("./examples/apps_multiple.py") as engine:
        resp = engine.get ("/")
        assert "<title>Skitai WSGI App Engine</title>" in resp.text

        resp = engine.get ("/reindeer")
        assert resp.status_code == 200

        resp = engine.get ("/imaginary-snake.jpg")
        assert resp.status_code == 404

        with pytest.raises (ProtocolError):
            with engine.rpc ("/") as stub:
                stub.add_number (1, 2)

        with engine.rpc ("/myrpc") as stub:
            assert stub.add_number (1, 2) == 3