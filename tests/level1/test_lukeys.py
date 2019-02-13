from confutil import rprint
import time
import random
import pytest
from unittest.mock import MagicMock
from skitai.wastuff.semaps import Semaps

def test_models_in_storage (wasc):
	was = wasc ()
	was._luwatcher = Semaps (["a", "b"])	
	was.apps = MagicMock ()
	was.setlu ('a')
	assert time.time () - was.getlu ('a') < 1
	assert was.getlu ('b') == was.init_time	
	was.setlu ('b')
	assert time.time () - was.getlu ('b') < 1
	
	