from rs4 import logger
from aquests.client import adns 
from rs4 import asyncore

from test_adns import loop
    
def callback1 (ans):
    assert ans [-1]["data"]

def callback2 (ans):
    assert ans [0]["status"] == "NXDOMAIN"

def callback3 (ans):
    assert ans [0]["error"] == "too many error"    
    
def test_adns ():
    adns.init (logger.screen_logger (), [], "tcp")
    adns.query ("www.microsoft.com", "A", callback1)
    loop ()
    
    adns.query ("www.cnn.comx", "A", callback2)
    adns.query ("www.cnn.comx", "A", callback2)
    loop ()    
    adns.query ("www.cnn.comx", "A", callback2)
    loop ()
    
    # 3 strike error!
    adns.query ("www.cnn.comx", "A", callback3)
    loop ()
    
    ans = adns.get ("www.cnn.comx", "A")
    assert ans [0]["error"] == "too many error"
    
        
        
        
        