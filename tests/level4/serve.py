import skitai
import atila
import atila_vue
import tfserver
import delune
import exts.tfserver
import exts.delune
import os
import pwa

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
        pref.set_static ('/', 'pwa/static')
        pref.extends (atila_vue)
        skitai.mount ('/', pwa, pref, subscribe = ['delune', 'tfserver'])

    skitai.run (ip = '0.0.0.0', name = 'big-picture')
