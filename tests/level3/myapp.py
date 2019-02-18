from atila import Atila

app = Atila (__name__)
  
@app.route ("/")
def index (was):
  return "<h1>something</h1>"

@app.route ("/apis/pets/<int:id>")  
def pets (was, id):
  return was.response.API ({"id": id, "kind": "dog", "name": "Monk"})

def mount (app):
    @app.route ("/apis/owners/<int:id>")
    def owners (was, id):
        return was.response.API ({"id": id, "name": "Monk"})
    
    