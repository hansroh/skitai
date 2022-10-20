from . import sub, sub2, sub10

def __request__ (context):
    context.request.g.K = [1]
    context.request.g.A = ['a']

def __wrapup__ (context, content):
    pass

def __error__ (context, exception):
    pass

def __teardown__ (context):
    context.request.g.A.append ('b')

def __setup__ (context):
    app = context.app
    app.mount ('/', sub)
    app.mount ('/sub2', sub2)
    app.mount ('/sub10', sub10)

def __mounted__ (context):
    pass

def __mount__ (context):
    @context.app.route ('/')
    def index (context):
        assert context.request.g.A == ['a']
        assert context.request.g.K == [1]
        return 'pwa'

def __umount__ (context):
    pass
