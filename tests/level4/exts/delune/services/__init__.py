
def __mount__ (app, mntopt):
    @app.route ('/delune-ext')
    def index (was):
        return 'delune-ext'
