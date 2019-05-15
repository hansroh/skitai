
def foo (a):
    return "echo:" + a

def test_was_async_requests (async_wasc):
    was = async_wasc ()    
    future, actives = was.create_thread (foo, 'hello')
    assert actives == 1
    assert future.result () == "echo:hello"

    future, actives = was.create_process (foo, 'hello')
    assert actives == 1
    assert future.result () == "echo:hello"
