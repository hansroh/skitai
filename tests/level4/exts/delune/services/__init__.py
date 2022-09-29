
def __mount__ (context, app, opts):
    @app.route ('/delune-ext')
    def index (context):
        return 'delune-ext'
