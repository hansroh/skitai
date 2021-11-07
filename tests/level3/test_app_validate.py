from skitai.exceptions import HTTPError
import pytest
import re
import uuid

class R:
    def __init__ (self, args):
        self.ARGS = args

def test_app_validator (wasc, app):
    assert not app.validate (R ({'a': 1}), required = ["a"])
    assert not app.validate (R ({'a': 1}), protected = ["b"])
    with pytest.raises (HTTPError):
        app.validate (R ({'a': 1}), protected = ["a"])
    with pytest.raises (HTTPError):
        app.validate (R ({'a': None}), protected = ["a"])
    with pytest.raises (HTTPError):
        app.validate (R ({'a': 1}), required = ["b"])
    with pytest.raises (HTTPError):
        app.validate (R ({'a': None}), required = ["a"])
    with pytest.raises (HTTPError):
        app.validate (R ({'a': ''}), required = ["a"])
    assert not app.validate (R ({'a': 1}), a = int)
    assert not app.validate (R ({'a': 1}), a = 1)
    with pytest.raises (HTTPError):
        app.validate (R ({'a': 1}), a = str)
    with pytest.raises (HTTPError):
        app.validate (R ({'a': 1}), a = dict)
    assert not app.validate (R ({'a': {}}), a = dict)

    assert not app.validate (R ({'a': {}}), oneof = ['a', 'b'])
    with pytest.raises (HTTPError):
        app.validate (R ({'a': 1}), oneof = ['b', 'c'])
    assert not app.validate (R ({'a': 'k'}), a = re.compile ('^k'))
    with pytest.raises (HTTPError):
        app.validate (R ({'a': 'p'}), a = re.compile ('^k'))
    with pytest.raises (HTTPError):
        app.validate (R ({'a': 1}), a = re.compile ('^k'))

    assert not app.validate (R ({'a': '1234'}), a__len__lte = 4)
    with pytest.raises (HTTPError):
        app.validate (R ({'a': '1234'}), a__len__lte = 3)
    assert not app.validate (R ({'a': '1234'}), a__contains = '23')
    assert not app.validate (R ({'a': '1234'}), a__endswith = '4')
    assert not app.validate (R ({'a': '1234'}), a__startswith = '1')
    assert not app.validate (R ({'a': '1234'}), a__notstartwith = '2')
    assert not app.validate (R ({'a': '1234'}), a__notendwith = '2')

    assert not app.validate (R ({'a': '1234'}), a__gt = 1)
    with pytest.raises (HTTPError):
        app.validate (R ({'a': '1234'}), a__lt = 100)

    assert not app.validate (R ({'a': 'a'}), a__in = ["a", "b"])
    assert not app.validate (R ({'a': 'a'}), a__notin = ["b", "c"])
    with pytest.raises (HTTPError):
        app.validate (R ({'a': 'a'}), a__notin = ["a", "c"])

    assert not app.validate (R ({'a': '2'}), a__between = (1, 4))
    assert not app.validate (R ({'a': 2}), a__between = (1, 4))

    with pytest.raises (HTTPError):
        app.validate (R ({'a': 'a'}), a__between = (1, 4))
    with pytest.raises (HTTPError):
        app.validate (R ({'a': '5'}), a__between = (1, 4))

    assert not app.validate (R ({'a': 4}), ints = ["a"])
    assert not app.validate (R ({'a': 4.1}), ints = ["a"])
    with pytest.raises (HTTPError):
        app.validate (R ({'a': "4.1"}), ints = ["a"])

    assert not app.validate (R ({'a': [1]}), lists = ["a"])
    assert not app.validate (R ({'a': 'as@asda.com'}), emails = ["a"])

    with pytest.raises (HTTPError):
        app.validate (R ({'a': 'asasda.com'}), emails = ["a"])
    with pytest.raises (HTTPError):
        app.validate (R ({'a': 'asasda.com'}), uuids = ["a"])
    assert not app.validate (R ({'a': str (uuid.uuid4 ())}), uuids = ["a"])

    assert not app.validate (R ({'a': 'as@asda.com'}), strings = ["a"])
    assert not app.validate (R ({'a': 'as@asda.com'}), strs = ["a"])

    assert not app.validate (R ({'a': 'as@asda.com'}), safes = ["a"])
    with pytest.raises (HTTPError):
        app.validate (R ({'a': '<script>'}), safes = ["a"])
    with pytest.raises (HTTPError):
        app.validate (R ({'a': '<script src="">'}), safes = ["a"])
    with pytest.raises (HTTPError):
        app.validate (R ({'a': '="javascript:'}), safes = ["a"])
    app.validate (R ({'a': '<a>'}), notags = ["a"])

    assert not app.validate (R ({'a': 'a'}), a__eq = 'a')
    assert not app.validate (R ({'a': 'a'}), a__neq = 'b')
    with pytest.raises (HTTPError):
        app.validate (R ({'a': 'a'}), a__eq = 'b')
    with pytest.raises (HTTPError):
        app.validate (R ({'a': 'a'}), a__neq = 'a')

    assert not app.validate (R ({'a': '1234'}), a__len__between = (1, 5))
    with pytest.raises (HTTPError):
        app.validate (R ({'a': '1234'}), a__len__between = (1, 3))

    assert not app.validate (R ({'a': {"c": "c"}}), required = ["a.c"])
    with pytest.raises (HTTPError):
        app.validate (R ({'a': {"c": "c"}}), required = ["a.b"])

    assert not app.validate (R ({'b': {"c": "c"}}), protected = ["a.c"])
    assert not app.validate (R ({'a': {"b": "c"}}), protected = ["a.c"])
    with pytest.raises (HTTPError):
        app.validate (R ({'a': {"c": "c"}}), protected = ["a.c"])

