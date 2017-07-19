from skitai.server.wastuff import fakewas
from skitai.saddle import Saddle

app = Saddle (__name__)
was = fakewas.build (app)
print (was)
