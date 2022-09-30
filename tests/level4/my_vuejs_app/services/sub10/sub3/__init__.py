def __mount__ (context, app, opts):
    @app.route ("")
    def index (context):
        return "sub3"
