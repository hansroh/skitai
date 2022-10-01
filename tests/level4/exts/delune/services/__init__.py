
def __mount__ (context, app, opts):
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
