import pytest
from functools import partial
import skitai

@pytest.fixture
def launch ():
    return partial (skitai.launch, port = 30371, silent = False)
