from rs4.attrdict import AttrDictTS
import pytest

def test_g ():
    g = AttrDictTS ()
    g ['a'] = 1
    assert g ['a'] == 1
    assert g.a == 1

    g.a = 2
    assert g.a == 2
    assert g ['a'] == 2

    del g.a
    with pytest.raises (KeyError):
        assert g.a == 2

    g.__b__ = 2
    assert g.__b__ == 2
    assert g ['__b__'] == 2

    del g.__b__
    with pytest.raises (KeyError):
        assert g.__b__ == 2


