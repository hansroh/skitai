from . import sub, sub2

def __setup__ (app, mntopt):
    app.mount ('/', sub)
    app.mount ('/sub2', sub2)

def __mount__ (app, mntopt):
    @app.mounted
    def mounted (was):
        pass

    @app.route ('/')
    def index (was):
        return 'pwa'

def __umount__ (app):
    pass
