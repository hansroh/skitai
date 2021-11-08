import pytest
from functools import partial
import skitai
import platform
import sys
import os

IS_PYPY = platform.python_implementation() == 'PyPy'

@pytest.fixture
def launch ():
    return partial (skitai.test_client, port = 30371, silent = False)

