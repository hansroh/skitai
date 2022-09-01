async def __request__ (context, app, opts):
    context.request.g.K.append (4)

async def __ok__ (context, app, opts, content):
    content += "-async"
    return content

def __mount__ (context, app, opts):
    @app.route ("")
    def index (context):
        assert context.request.g.A == ['a']
        assert context.request.g.K == [1, 2, 4]
        return "sub4"

    @app.route ("/async")
    async def index2 (context):
        assert context.request.g.A == ['a']
        assert context.request.g.K == [1, 2, 4]
        return "sub4"