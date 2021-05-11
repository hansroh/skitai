from . import sub5

def __setup__ (app, mntopt):
    app.mount ('/sub5', sub5)

def __mount__ (app, mntopt):
    @app.route ("")
    def index (was):
        return "sub4"
