
def __mount__ (app, mntopt):
    @app.route ('/models/tfserver')
    def index (context):
        return 'tfserver'
