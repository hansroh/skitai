import skitai
import sys

def test_preference ():
    with skitai.preference () as pref:
        assert pref.config == {}

    with skitai.preference (True) as pref:
        assert 'MAX_UPLOAD_SIZE' in pref.config
        assert pref.mountables == []
        pref.mount_later ("/", "app.py")
        assert pref.mountables [0] == (('/', 'app.py'), {})

        pref.set_static ('/staticx', 'examples/staticd')
        assert pref.config.STATIC_URL == '/staticx'

        pref.set_media ('/mediax', 'examples/staticd')
        assert pref.config.MEDIA_URL == '/mediax'


    f = sys.path [0]
    with skitai.preference (False, './') as pref:
        assert f != sys.path [0]
    sys.path.pop (0)
    assert f == sys.path [0]