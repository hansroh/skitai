import time
import pytest
import sys

def foo (a):
    time.sleep (1.0)
    return "echo:" + a

def foo2 (a):
    xx

def test_was_requests (Context):
    def callback (was, task):
        assert not task.fetch ()

    was = Context ()
    future = was.Thread (foo, 'hello')
    assert future.result () == "echo:hello"
    data = was.Thread (foo, 'hello').returning ("then")
    assert data == "then"
    future = was.Process (foo, 'hello')
    assert future.result () == "echo:hello"
    data = was.Process (foo, 'hello').returning ("then")
    assert data == "then"

def test_was_requests2 (Context):

    was = Context ()
    for i in range (10):
        future = was.Thread (foo, 'hello')
    assert future.result () == "echo:hello"

    for i in range (10):
        future = was.Process (foo, 'hello')
    assert future.result () == "echo:hello"

    future = was.Thread (foo2, 'hello')
    future = was.Process (foo2, 'hello')

    time.sleep (15)
    assert was.executors.cleanup () == [0, 0]
