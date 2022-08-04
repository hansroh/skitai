
def __mount__ (app):
    @app.route ("")
    def sub (context):
        return "i am sub"
