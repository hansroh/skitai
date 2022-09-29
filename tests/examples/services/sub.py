
def __mount__ (context, app, opts):
    @app.route ("")
    def sub (context):
        return "i am sub"
