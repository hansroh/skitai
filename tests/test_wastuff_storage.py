from confutil import rprint
import time
import random
import pytest
from mock import MagicMock

def test_models_in_storage (wasc):
	was = wasc ()
	was.apps = MagicMock ()
	was.setlu ('a')
	assert time.time () - was.getlu ('a') < 1
	assert was.getlu ('b') == was.init_time
	