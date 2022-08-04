from confutil import rprint
import time
import random
import pytest
from unittest.mock import MagicMock
from skitai.wastuff.semaps import Semaps

def test_models_in_storage (Context):
	context = Context ()
	context._luwatcher = Semaps (["a", "b"])
	context.apps = MagicMock ()
	context.setlu ('a')
	assert time.time () - context.getlu ('a') < 1
	assert context.getlu ('b') == context.init_time
	context.setlu ('b')
	assert time.time () - context.getlu ('b') < 1

