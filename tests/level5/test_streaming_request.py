import sys
import rs4
import pytest
import time

def stream (blocksize = 4096):
    chunks = 100
    while chunks:
        data = b'a' * blocksize
        if not data:
            break
        print ('send', blocksize)
        yield data
        chunks -= 1

def test_stream ():
    for x in stream ():
        assert len (x) == 4096
