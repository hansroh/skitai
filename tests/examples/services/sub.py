
def __mount__ (app):
    @app.route ("")
    def sub (was):
        return "i am sub"
