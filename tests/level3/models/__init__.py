import sys, os
from rs4 import pathtool

BASE_DIR = os.path.abspath (os.path.dirname (__file__))

def __config__ (pref):
    import skitai
    from config import settings

    static = os.path.join (BASE_DIR, 'static')
    pathtool.mkdir (static)
    skitai.mount (settings.STATIC_URL, static)
    skitai.log_off (settings.STATIC_URL)
    pref.config.SETTINGS = settings
