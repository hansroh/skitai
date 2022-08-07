import requests
import platform
import psutil
import os

REPEAT = 100

def memory_usage ():
    process = psutil.Process (os.getpid())
    mem = process.memory_info()[0]
    return mem

def test_app (launch):
    if os.getenv ('GITLAB_CI'):
        return
    with launch ("./examples/app2.py") as engine:
        beginwith = memory_usage ()
        for i in range (REPEAT):
            resp = engine.get ('/threaproducer?n=200&max_size=20')
            assert resp.status_code == 200
            assert len (resp.data) == 100000
            assert memory_usage () - beginwith < 20000
        assert memory_usage () - beginwith < 20000
