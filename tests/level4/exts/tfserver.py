
def __mount__ (context, app, opts):
    @app.route ('/models/tfserver')
    def index (context):
        return 'tfserver'
