import skitai
from atila import Override
import atila_vue
import tfserver
import delune
import exts.tfserver
import exts.delune
import os
import my_vuejs_app
from rs4 import pathtool

os.environ ['SECRET_KEY'] = 'SECRET_KEY'

if __name__ == '__main__':
    with skitai.preference () as pref:
        skitai.mount ('/', Override (tfserver, exts.tfserver), pref)

    with skitai.preference () as pref:
        pref.config.resource_dir = skitai.joinpath ('exts/delune/resources')
        pref.set_static ('/static/delune', 'exts/delune/static')
        skitai.mount ('/delune', Override (delune, exts.delune), pref)

    with skitai.preference () as pref:
        pref.set_static ('/', 'my_vuejs_app/static')
        app = Override (atila_vue, my_vuejs_app).create_app (my_vuejs_app)
        skitai.mount ('/', app, pref, subscribe = ['delune', 'tfserver'])

    skitai.enable_file_logging ("/tmp")
    skitai.run (ip = '0.0.0.0', name = 'big-picture', tasks = 4)
