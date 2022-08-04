from . import sub3, sub4

def __setup__ (app, mntopt):
    app.mount ("/sub3", sub3)
    app.mount ("/sub4", sub4)


def __mount__ (app, mntopt):
    @app.route ("")
    def index (context):
        return "sub10"
