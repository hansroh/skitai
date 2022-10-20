from . import sub3, sub4

def __request__ (context):
    context.request.g.K.append (2)

def __wrapup__ (context, content):
    content += "-trailer"
    return content

def __setup__ (context):
    context.app.mount ("/sub3", sub3)
    context.app.mount ("/sub4", sub4)


def __mount__ (context):
    @context.app.route ("")
    def index (context):
        assert context.request.g.A == ['a']
        assert context.request.g.K == [1, 2]
        return "sub2"

    @context.app.route ("/async")
    async def index2 (context):
        assert context.request.g.A == ['a']
        assert context.request.g.K == [1, 2]
        return "sub2"