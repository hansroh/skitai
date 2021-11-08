import requests
import platform

def test_app (launch):
    with launch ("./examples/app2.py") as engine:
        for i in range (10000):
            resp = engine.get ('/threaproducer?n=200&q=20')
            assert resp.status_code == 200
            assert len (resp.data) == 20480

