import atila
import asyncio
import skitai

app = atila.Atila (__name__)

@app.route ('/')
def index (context):
    return 'Hello Atila'

@app.route ("/str")
async def a (context):
    await asyncio.sleep (1)
    return "100"

@app.route ("/api")
async def b (context):
    await asyncio.sleep (1)
    return context.API (x = 100)

if __name__ == '__main__':
    skitai.mount ('/statics', 'statics')
    skitai.mount ("/", app)
    skitai.enable_async ()
    skitai.run (
		workers = 3,
		address = "0.0.0.0",
		port = 30371
	)
