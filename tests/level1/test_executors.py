import time
import pytest

def foo (a):
    time.sleep (1.0)
    return "echo:" + a

def foo2 (a):
    xx    

def test_was_async_requests (async_wasc):
    def callback (was, task):
        assert not task.fetch ()

    was = async_wasc ()
    future = was.Thread (foo, 'hello')
    assert future.result () == "echo:hello"
    data = was.Thread (foo, 'hello').asac ("then")
    assert data == "then"
    future = was.Process (foo, 'hello')    
    assert future.result () == "echo:hello"
    data = was.Process (foo, 'hello').asac ("then")
    assert data == "then"

def test_was_async_requests2 (async_wasc):    
    was = async_wasc ()    
    for i in range (10):
        future = was.Thread (foo, 'hello')        
    assert future.result () == "echo:hello"

    for i in range (10):
        future = was.Process (foo, 'hello')            
    assert future.result () == "echo:hello"
    
    future = was.Thread (foo2, 'hello')            
    future = was.Process (foo2, 'hello')

    time.sleep (3)
    assert was.executors.cleanup () == [0, 0]


    

    