def __mount__ (app, mntopt):
    @app.route ("")
    def index (context):
        return "sub4"
