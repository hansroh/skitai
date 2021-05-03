import skitai
from skitai import was
import os
import pytest

try:
    import django
except ImportError:
    django = None

def test_skitai (app):
    skitai.set_worker_critical_point ()

    skitai.register_states ("a", "b")
    if was._started ():
        assert was._luwatcher._keys == ['a', 'b']
    else:
        assert skitai.dconf ["models_keys"] == {"a", "b"}

    if os.name != "posix":
        return

    skitai.dconf ['mount']["default"] = []
    assert skitai.joinpath ('a', 'b').endswith ("/bin/a/b")
    skitai.mount ("/k", app)
    assert skitai.dconf ['mount']["default"][0][1][0].endswith ('/bin/pytest')
    assert skitai.dconf ['mount']["default"][0][1][1] == 'app'

    skitai.dconf ['mount']["default"] = []
    skitai.mount ("/k2", '/path/app.py', 'app')
    assert skitai.dconf ['mount']["default"][0][1] == ('/path/app.py', 'app')

    skitai.dconf ['mount']["default"] = []
    skitai.mount ("/k2", 'path/app.py', 'app')
    assert skitai.dconf ['mount']["default"][0][1][0].endswith ('/bin/path/app.py')
    assert skitai.dconf ['mount']["default"][0][1][1] == 'app'

    skitai.dconf ['mount']["default"] = []
    skitai.mount ("/k2", "X11")
    assert skitai.dconf ['mount']["default"][0][1][0].endswith ('/bin/X11')

    skitai.dconf ['mount']["default"] = []
    skitai.mount ("/k2", "@X11")
    assert skitai.dconf ['mount']["default"][0][1] == "@X11"

    if django:
        skitai.dconf ['mount']["default"] = []
        t = os.path.join (os.path.dirname (__file__), "django_")
        skitai.mount ("/k2", t)
        assert skitai.dconf ['mount']["default"][0][1] == t

        skitai.dconf ['mount']["default"] = []
        t = os.path.join (os.path.dirname (__file__), "django_", "wsgi.py")
        skitai.mount ("/k2", t, "application")

        t = os.path.join (os.path.dirname (__file__), "django_", "settings.py")
        skitai.alias ("@django", skitai.DJANGO, t)
        assert skitai.dconf ["clusters"]["django"]
