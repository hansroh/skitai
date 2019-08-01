import skitai
import sys

def test_getopt ():    
    opts, args = skitai.getopt ("shf:x", ["ssl", "debug", "origin="])
        