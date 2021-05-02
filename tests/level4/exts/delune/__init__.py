from . import services

def __setup__ (app, mntopt):
    app.mount ('/', services)
