import pytest
import sys, os
import time
from rs4.protocols import aquests
from test_aquests_example_apps import assert_status, makeset

def test_https (launch):
	global ERRS
	ERRS = 0
	with launch ("./examples/https.py", ssl = True) as engine:
		aquests.configure (2, callback = assert_status)
		[ makeset (1) for i in range (2) ]
		aquests.fetchall ()
		assert ERRS < 4
