import pytest
from functools import partial
import skitai

@pytest.fixture
def launch ():
    return partial (skitai.test_client, port = 30371, silent = False)
