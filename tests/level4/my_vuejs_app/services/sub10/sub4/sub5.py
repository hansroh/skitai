
def __mount__ (context):
    @context.app.route ("")
    def index (context):
        return "sub5"
