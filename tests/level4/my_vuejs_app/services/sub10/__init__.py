from . import sub3, sub4

def __setup__ (context):
    context.app.mount ("/sub3", sub3)
    context.app.mount ("/sub4", sub4)


def __mount__ (context):
    @context.app.route ("")
    def index (context):
        return "sub10"
