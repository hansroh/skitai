import pytest
from functools import partial
import skitai
from atila.pytest_hooks import *

@pytest.fixture
def launch (dryrun):
    return partial (skitai.test_client, port = 30371, silent = False, dry = dryrun)

