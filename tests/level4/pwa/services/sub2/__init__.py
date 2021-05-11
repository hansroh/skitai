from . import sub3

def __setup__ (app, mntopt):
    app.mount ("/sub3", sub3)

def __mount__ (app, mntopt):
    @app.route ("")
    def index (was):
        return "sub2"
