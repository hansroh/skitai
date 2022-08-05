from atila import Atila

app = Atila (__name__)

@app.route ("/")
def index (context):
  return "<h1>something</h1>"

@app.route ("/apis/pets/<int:id>")
def pets (context, id):
  return context.response.API ({"id": id, "kind": "dog", "name": "Monk"})

def __mount__ (context, app, opts):
    @app.route ("/apis/owners/<int:id>")
    def owners (context, id):
        return context.response.API ({"id": id, "name": "Monk"})

