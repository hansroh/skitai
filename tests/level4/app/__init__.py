import atila
import atila_vue
import os
from . import services

def __config__ (pref):
    pref.config.FRONTEND = {}

def __app__ ():
    app = atila.Atila (__name__)
    app.mount ('/', services)
    return app

def __mount__ (app, mntopt):
    @app.route ('/urlspecs')
    def urlspecs (context):
        return context.API (urlspecs = context.app.get_urlspecs ())
