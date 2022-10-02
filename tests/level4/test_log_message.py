import sys
import os

def test_debug_log (launch):
    try:
        import tfserver
    except ImportError:
        return

    for name in ('app', 'request', 'server'):
        try:
            os.remove (f"/tmp/{name}.log")
        except FileNotFoundError:
            pass

    serve = './level4/serve.py'
    with launch (serve, port = 30371) as engine:
        pass

    with open ("/tmp/app.log") as f:
        d = f.read ()
    assert d.count ("is overridden") == 5
    assert d.count ("is replaced") == 2
    assert d.count ("unmounted") == 23

