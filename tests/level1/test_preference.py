import skitai
import sys

def test_preference ():
    with skitai.preference () as pref:
        assert pref.config == {}

    with skitai.preference (True) as pref:
        assert 'max_cache_size' in pref.config
        assert pref.mountables == []
        pref.mount ("/", "app.py")
        assert pref.mountables [0] == (('/', 'app.py'), {})

    f = sys.path [0]
    with skitai.preference (False, './') as pref:
        assert f != sys.path [0]
    sys.path.pop (0)
    assert f == sys.path [0]