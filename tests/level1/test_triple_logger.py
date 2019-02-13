import pytest
from skitai.wastuff import triple_logger
from rs4 import  pathtool, logger as rlog
import shutil, os, glob, time
	
def test_tirple_logger ():
	rlog.rotate_logger.PRESERVE_MAX = 3
	
	logpath = './unitests/logs'
	logger = triple_logger.Logger ("screen", None)
	assert len (logger.logger_factory) == 3
	logger = triple_logger.Logger (["file", "screen"], logpath)
	assert os.path.isfile (os.path.join (logpath, 'request.log'))
	logger.rotate ()	
	logger.rotate ()	
	print (glob.glob (os.path.join (logpath, 'request-*')))
	assert len (glob.glob (os.path.join (logpath, 'request-*'))) == 2
	for i in range (5):
		logger.rotate ()
		time.sleep (1)
	
	assert len (glob.glob (os.path.join (logpath, 'request-*'))) == 3
	logger.close ()
	shutil.rmtree ('./unitests')
	assert not os.path.isfile (logpath)
