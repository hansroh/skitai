from skitai.wastuff import autoconf
from skitai.testutil import offline
import shutil
from rs4 import pathtool
import os

def test_autoconf ():
    try:
        offline.activate ()
        offline.install_vhost_handler ()
        offline.mount ("/", "level0")
        offline.mount ("/level1", "level1")
        vhost = offline.wasc.httpserver.handlers [0].get_vhost ("default")

        project_root = './examples/autoconf'
        if os.path.isdir (project_root):
            shutil.rmtree (project_root)
        pathtool.mkdir (project_root)
        conf = dict (
            name = 'testapp',
            port = 5000,
        )
        autoconf.generate (project_root, vhost, conf)
    finally:
        offline.wasc.close ()

