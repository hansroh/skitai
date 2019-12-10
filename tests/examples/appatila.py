import atila

app = atila.Atila (__name__)
@app.route ('/')
def index (was):
    return 'Hello Atila'