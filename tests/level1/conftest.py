import pytest
from skitai.testutil import offline

@pytest.fixture (scope = "session")
def wasc ():
    offline.activate (make_sync = False)
    yield offline.wasc
    offline.wasc.close ()
