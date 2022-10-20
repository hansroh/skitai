
def __mount__ (context):
    @context.app.route ("")
    def sub (context):
        return "i am sub"
