import pytest
import requests
import time

def test_reload (launch):
    with open ("./examples/services/sub.py") as f:
        data = f.read ()
        data = data.replace ("i am resub", "i am sub")
    with open ("./examples/services/sub.py", "w") as f:
        f.write (data)

    with launch ("./examples/apps_multiple.py") as engine:
        resp = requests.get ("http://127.0.0.1:30371/sub")
        assert resp.status_code == 200
        assert "i am sub" in resp.text

        with open ("./examples/services/sub.py") as f:
            data = f.read ()
            data = data.replace ("i am sub", "i am resub")
        with open ("./examples/services/sub.py", "w") as f:
            f.write (data)

        time.sleep (2)
        resp = requests.get ("http://127.0.0.1:30371/sub")
        assert resp.status_code == 200
        assert "i am resub" in resp.text

        with open ("./examples/services/sub.py") as f:
            data = f.read ()
            data = data.replace ("i am resub", "i am sub")
        with open ("./examples/services/sub.py", "w") as f:
            f.write (data)

        time.sleep (0.3)
        resp = requests.get ("http://127.0.0.1:30371/sub")
        assert resp.status_code == 200
        assert "i am resub" in resp.text, "under 1 sec, must not reload"

        time.sleep (2)
        resp = requests.get ("http://127.0.0.1:30371/sub")
        assert resp.status_code == 200
        assert "i am sub" in resp.text
