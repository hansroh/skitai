import pytest
from skitai.testutil import offline

@pytest.fixture (scope = "session")
def Context ():
    offline.activate ()
    yield offline.wasc
    offline.wasc.cleanup ()
