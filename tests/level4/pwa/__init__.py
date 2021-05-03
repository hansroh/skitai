import atila
import atila_vue
import os
from . import services

def __app__ ():
    app = atila.Atila (__name__)
    app.mount ('/', services)
    return app

