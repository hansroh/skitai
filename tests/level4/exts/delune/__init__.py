from . import services

def __setup__ (context, app, opts):
    app.mount ('/', services)
