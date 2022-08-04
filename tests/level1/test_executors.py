import time
import pytest
import sys

def foo (a):
    time.sleep (1.0)
    return "echo:" + a

def foo2 (a):
    xx

def test_was_requests (Context):
    def callback (context, task):
        assert not task.fetch ()

    context = Context ()
    future = context.Thread (foo, 'hello')
    assert future.result () == "echo:hello"
    data = context.Thread (foo, 'hello').returning ("then")
    assert data == "then"
    future = context.Process (foo, 'hello')
    assert future.result () == "echo:hello"
    data = context.Process (foo, 'hello').returning ("then")
    assert data == "then"

def test_was_requests2 (Context):

    context = Context ()
    for i in range (10):
        future = context.Thread (foo, 'hello')
    assert future.result () == "echo:hello"

    for i in range (10):
        future = context.Process (foo, 'hello')
    assert future.result () == "echo:hello"

    future = context.Thread (foo2, 'hello')
    future = context.Process (foo2, 'hello')

    time.sleep (15)
    assert context.executors.cleanup () == [0, 0]
