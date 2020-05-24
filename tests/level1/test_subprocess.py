import time
import pytest
import sys
from concurrent.futures._base import TimeoutError
from rs4 import logger

def foo (task):
    assert b'total' in task.fetch ()

def test_subprocess (async_wasc):
    def callback (was, task):
        assert not task.fetch ()

    was = async_wasc ()
    task = was.Subprocess ('ls -al')
    assert 'total' in task.fetch ()

    task = was.Subprocess ('ls --fff')
    with pytest.raises (SystemError):
        task.fetch ()
    try:
        task.fetch ()
    except:
        assert '--fff' in logger.trace ()

    task = was.Subprocess ("{} -c 'import time;time.sleep (3)'".format (sys.executable))
    with pytest.raises (TimeoutError):
        task.fetch (timeout = 1)
