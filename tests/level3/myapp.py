from atila import Atila
from skitai import was as cwas

app = Atila (__name__)

@app.route ("/")
def index (was):
  return "<h1>something</h1>"

@app.route ("/apis/pets/<int:id>")
def pets (was, id):
  return was.response.API ({"id": id, "kind": "dog", "name": "Monk"})

@app.route ("/apis/was")
def checkwas (was):
    return was.API (a = hasattr (was, "request"), b = hasattr (cwas, "request"))

def __mount__ (app):
    @app.route ("/apis/owners/<int:id>")
    def owners (was, id):
        return was.response.API ({"id": id, "name": "Monk"})

