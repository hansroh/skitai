
def __mount__ (app, mntopt):
    @app.route ('/delune-ext')
    def index (context):
        return 'delune-ext'
