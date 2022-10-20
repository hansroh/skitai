from . import services

def __setup__ (context):
    context.app.mount ('/', services)
