import pytest
from functools import partial
from skitai.testutil.launcher import Launcher

@pytest.fixture
def launch ():
    return partial (Launcher, port = 30371, silent = False)
