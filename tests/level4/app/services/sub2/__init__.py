from . import sub3, sub4

def __request__ (context, app, opts):
    context.request.g.K.append (2)

def __ok__ (context, app, opts, content):
    content += "-trailer"
    return content

def __setup__ (context, app, opts):
    app.mount ("/sub3", sub3)
    app.mount ("/sub4", sub4)


def __mount__ (context, app, opts):
    @app.route ("")
    def index (context):
        assert context.request.g.A == ['a']
        assert context.request.g.K == [1, 2]
        return "sub2"

    @app.route ("/async")
    async def index2 (context):
        assert context.request.g.A == ['a']
        assert context.request.g.K == [1, 2]
        return "sub2"