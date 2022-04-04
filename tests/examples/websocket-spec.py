from atila import Atila
import skitai
import atila

app = Atila (__name__)

app.access_control_allow_origin = ["*"]
app.debug = True
app.use_reloader = True
app.securekey = 'asdadada'

@app.route ("/coroutine")
@app.websocket (skitai.WS_COROUTINE, 60)
def echo_coroutine (was):
	n = 0
	while 1:
		msg = yield was.Input ()
		if not msg:
			break
		yield 'echo: ' + msg
		n += 1
		if n % 3 == 0:
			yield 'double echo: ' + msg


@app.route ("/chatty")
@app.websocket (atila.WS_CHANNEL, 60)
def echo4 (was):
	n = 0
	while 1:
		n += 1
		msg = yield
		if n == 1:
			yield '1st: ' + msg
		elif n == 2:
			was.websocket.send ('pre2nd: ' + msg)
			yield (
				'2nd: ' + msg,
				'post2nd: ' + msg
			)
		else:
			yield 'many: ' + msg

def onopenp (was):
  was.session.set ("WS_ID", was.websocket.client_id)
  was.websocket.send ("hi")

def onclosep (was):
  was.session.remove ("WS_ID")

@app.route ("/reporty")
@app.websocket (atila.WS_SESSION, 1200, onopenp, onclosep)
def reporty (was, message, a, b = '2', **payload):
	was.websocket.send ("first message")
	return f'{a}: {message}'


@app.route ("/reporty/async")
@app.websocket (atila.WS_SESSION, 1200, onopenp, onclosep)
async def reporty_async (was, message, a, b = '2', **payload):
	was.websocket.send ("first message")
	return f'{a}: {message}'


if __name__ == "__main__":
	import skitai

	skitai.mount ("/websocket", app)
	skitai.run (port = 30371)
