from . import sub

def __setup__ (app, mntopt):
    app.mount ('/', sub)

def __mount__ (app, mntopt):
    @app.mounted
    def mounted (was):
        pass

    @app.route ('/')
    def index (was):
        return 'pwa'

def __umount__ (app):
    pass
