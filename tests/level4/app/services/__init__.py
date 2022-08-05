from . import sub, sub2, sub10

def __setup__ (context, app, opts):
    app.mount ('/', sub)
    app.mount ('/sub2', sub2)
    app.mount ('/sub10', sub10)

def __mount__ (context, app, opts):
    @app.mounted
    def mounted (context):
        pass

    @app.route ('/')
    def index (context):
        return 'pwa'

def __umount__ (context, app, opts):
    pass
