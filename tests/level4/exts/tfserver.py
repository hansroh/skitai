
def __mount__ (app, mntopt):
    @app.route ('/models/tfserver')
    def index (was):
        return 'tfserver'
