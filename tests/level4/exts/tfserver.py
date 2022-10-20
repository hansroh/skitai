
def __mount__ (context):
    @context.app.route ('/models/tfserver')
    def index (context):
        return 'tfserver'
