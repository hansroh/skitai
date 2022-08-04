import skitai
import atila
import atila_vue
import tfserver
import delune
import exts.tfserver
import exts.delune
import os
import app

os.environ ['SECRET_KEY'] = 'SECRET_KEY'

if __name__ == '__main__':
    with skitai.preference () as pref:
        pref.overrides (exts.tfserver)
        skitai.mount ('/', tfserver, pref)

    with skitai.preference () as pref:
        pref.config.resource_dir = skitai.joinpath ('exts/delune/resources')
        pref.set_static ('/static/delune', 'exts/delune/static')
        pref.overrides (exts.delune)
        skitai.mount ('/delune', delune, pref)

    with skitai.preference () as pref:
        pref.set_static ('/', 'app/static')
        pref.extends (atila_vue)
        skitai.mount ('/', app, pref, subscribe = ['delune', 'tfserver'])

    skitai.run (ip = '0.0.0.0', name = 'big-picture')
