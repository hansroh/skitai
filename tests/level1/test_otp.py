from rs4.webkit import otp
import time
import random
import pytest

def test_otp ():
    salt = 'asd980asjoiasjdioadoadas80d80ad90a8d0k2j3432lsdaf'
    for i in range (100000):
        k = otp.generate (salt, random.randrange (-19, 20))
        v = otp.verify (k, salt)
        if k != v:
            print (k, v)
        assert v

    fails = 0
    for i in range (10000):
        k = otp.generate (salt, random.randrange (-40, -20))
        v = otp.verify (k, salt)
        if not v:
            fails += 1
    print (fails)
    assert fails > 5000

    fails = 0
    for i in range (10000):
        k = otp.generate (salt, random.randrange (20, 40))
        v = otp.verify (k, salt)
        if not v:
            fails += 1
    print (fails)
    assert fails > 5000

    fails = 0
    for i in range (10000):
        k = otp.generate (salt, random.randrange (-4000, -40))
        v = otp.verify (k, salt)
        if not v:
            fails += 1
    print (fails)
    assert fails == 10000

    fails = 0
    for i in range (10000):
        k = otp.generate (salt, random.randrange (40, 4000))
        v = otp.verify (k, salt)
        if not v:
            fails += 1
    print (fails)
    assert fails == 10000