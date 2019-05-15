import time

def foo (a):
    time.sleep (1.0)
    return "echo:" + a

def foo2 (a):
    xx    

def test_was_async_requests (async_wasc):
    was = async_wasc ()    
    future, actives = was.create_thread (foo, 'hello')
    assert actives == 1
    assert future.result () == "echo:hello"

    future, actives = was.create_process (foo, 'hello')
    assert actives == 1
    assert future.result () == "echo:hello"

def test_was_async_requests2 (async_wasc):
    was = async_wasc ()    
    for i in range (10):
        future, actives = was.create_thread (foo, 'hello')        
    assert future.result () == "echo:hello"

    for i in range (10):
        future, actives = was.create_process (foo, 'hello')            
    assert future.result () == "echo:hello"

    future, actives = was.create_process (foo2, 'hello')            
    future, actives = was.create_process (foo2, 'hello')
    assert was.executors.cleanup () == [0, 0]


    

    