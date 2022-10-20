from . import sub5

def __setup__ (context):
    context.app.mount ('/sub5', sub5)

def __mount__ (context):
    @context.app.route ("")
    def index (context):
        return "sub4"
