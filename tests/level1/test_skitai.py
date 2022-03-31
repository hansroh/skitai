import skitai
import os
import pytest

try:
    import django
except ImportError:
    django = None

def test_skitai (app):
    skitai.set_worker_critical_point ()

    skitai.register_states ("a", "b")
    if skitai.was._started ():
        assert skitai.was._luwatcher._keys == ['a', 'b']
    else:
        assert skitai.dconf ["models_keys"] == {"a", "b"}

    if os.name != "posix":
        return

    skitai.dconf ['mount']["default"] = []
    assert skitai.joinpath ('a', 'b').endswith ("/bin/a/b")
    skitai.mount ("/k", app)
    assert hasattr (skitai.dconf ['mount']["default"][0][1][0], 'app_name')

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
