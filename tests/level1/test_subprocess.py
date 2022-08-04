import time
import pytest
import sys
from concurrent.futures._base import TimeoutError
from rs4 import logger

def foo (task):
    assert b'total' in task.fetch ()

def test_subprocess (Context):
    def callback (context, task):
        assert not task.fetch ()

    context = Context ()
    task = context.Subprocess ('ls -al')
    assert 'total' in task.fetch ()

    task = context.Subprocess ('ls --fff')
    with pytest.raises (SystemError):
        task.fetch ()
    try:
        task.fetch ()
    except:
        assert '--fff' in logger.trace ()

    task = context.Subprocess ("{} -c 'import time;time.sleep (3)'".format (sys.executable))
    with pytest.raises (TimeoutError):
        task.fetch (timeout = 1)
