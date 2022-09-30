from . import sub3, sub4

def __setup__ (context, app, opts):
    app.mount ("/sub3", sub3)
    app.mount ("/sub4", sub4)


def __mount__ (context, app, opts):
    @app.route ("")
    def index (context):
        return "sub10"
