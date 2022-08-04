from . import sub, sub2, sub10

def __setup__ (app, mntopt):
    app.mount ('/', sub)
    app.mount ('/sub2', sub2)
    app.mount ('/sub10', sub10)

def __mount__ (app, mntopt):
    @app.mounted
    def mounted (context):
        pass

    @app.route ('/')
    def index (context):
        return 'pwa'

def __umount__ (app):
    pass
