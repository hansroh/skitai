import pytest
import skitai
import confutil
import threading
import time

def enforce ():
    time.sleep (2)
    ex = skitai.was.executors
    ex.executors [1].maintern (time.time ())
    ex.executors [1].shutdown ()

def foo (a, timeout = 0):
    time.sleep (timeout)
    return a        

    
def test_was_process (app):
    @app.route ("/")
    def index (was, timeout = 0):
        task = was.Process (foo, 'hello', int (timeout))
        return task.fetch ()
    
    @app.route ("/1")
    def index (was, timeout = 0):
        tasks = was.Tasks ([was.Process (foo, 'hello', int (timeout))])
        return tasks.fetch ()[0]

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.status_code == 200
        assert resp.data == 'hello'

        resp = cli.get ("/1")
        assert resp.status_code == 200
        assert resp.data == 'hello'

def test_was_thread (app):
    @app.route ("/")
    def index (was, timeout = 0):
        task = was.Thread (foo, 'hello', int (timeout))
        return task.fetch ()
    
    @app.route ("/1")
    def index (was, timeout = 0):
        tasks = was.Tasks ([was.Thread (foo, ['hello'], int (timeout))])
        return tasks.one ()[0]

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.status_code == 200
        assert resp.data == 'hello'

        resp = cli.get ("/1")
        assert resp.status_code == 200
        assert resp.data == 'hello'

def test_was_async_requests (app):
    @app.route ("/")
    def index (was, timeout = 0):
        def respond (was, task):
            assert task.fetch () == "hello"            
            return was.API ("201 Created")
        return was.Process (foo, 'hello', int (timeout)).then (respond)
    
    with app.test_client ("/", confutil.getroot ()) as cli:
        threading.Thread (target = enforce).start ()        
        resp = cli.get ("/")
        assert resp.status_code == 201

        time.sleep (3)
        threading.Thread (target = enforce).start ()
        resp = cli.get ("/?timeout=5")
        assert resp.status_code == 502
        

        

        