
def __mount__ (context):
    app = context.app
    @app.route ("/")
    def index (context):
        return '<h1>Custom Delune</h1>'

    @app.route ('/delune-ext')
    def index_ext (context):
        return 'delune-ext'

    @app.route ('/delune-ext')
    def index_ext (context):
        return 'delune-ext'

    @app.route ("/cols/<alias>/documents2/<_id>", methods = ["GET"])
    @app.route ("/cols/<alias>/documents/<_id>", methods = ["GET"])
    def get (context, alias, _id, nthdoc = 0):
        return ""

    @app.route ('/multi_route-3')
    @app.route ('/multi_route-2')
    @app.route ('/multi_route-1')
    def multi_route (context):
        return 'delune-ext'
