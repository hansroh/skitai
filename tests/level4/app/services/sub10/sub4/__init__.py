from . import sub5

def __setup__ (context, app, opts):
    app.mount ('/sub5', sub5)

def __mount__ (context, app, opts):
    @app.route ("")
    def index (context):
        return "sub4"
