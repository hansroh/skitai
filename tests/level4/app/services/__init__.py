from . import sub, sub2, sub10

def __request__ (context, app, opts):
    context.request.g.K = [1]

def __wrapup__ (context, app, opts, content):
    pass

def __error__ (context, app, opts, exception):
    pass

def __teardown__ (context, app, opts):
    pass

def __setup__ (context, app, opts):
    app.mount ('/', sub)
    app.mount ('/sub2', sub2)
    app.mount ('/sub10', sub10)

    @app.before_request
    def before_request (context):
        context.request.g.A = ['a']

    @app.teardown_request
    def teardown_request (context):
        context.request.g.A.append ('b')

def __mount__ (context, app, opts):
    @app.mounted
    def mounted (context):
        pass

    @app.route ('/')
    def index (context):
        assert context.request.g.A == ['a']
        assert context.request.g.K == [1]
        return 'pwa'

def __umount__ (context, app, opts):
    pass
