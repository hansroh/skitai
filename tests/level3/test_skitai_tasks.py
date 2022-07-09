import skitai
import confutil
import pprint
import re
import time

def hello (name):
    time.sleep (1)
    return f'hello, {name}'


def test_error_handler (app):
    @app.route ("/")
    def indexa (was):
        task1 = skitai.add_thread_task (hello, 'hans')
        task2 = skitai.add_process_task (hello, 'roh')
        task3 = skitai.add_subprocess_task ('ls -al')
        return was.API (
            a = task1.fetch (),
            b = task2.fetch (),
            c = task3.fetch (),
        )

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.status_code == 200
        assert resp.data ["a"] == "hello, hans"
        assert resp.data ["b"] == "hello, roh"
        assert "conftest.py" in resp.data ["c"]
