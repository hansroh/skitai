import pytest
from skitai import testutil

@pytest.fixture (scope = "session")
def wasc ():
    testutil.activate (make_sync = False)
    return testutil.wasc
    