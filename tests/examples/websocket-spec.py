from atila import Atila
import skitai
import atila

app = Atila (__name__)

app.access_control_allow_origin = ["*"]
app.debug = True
app.use_reloader = True
app.securekey = 'asdadada'


@app.route ("/chatty")
@app.websocket (atila.WS_CHATTY, 60)
def echo4 (context):
	n = 0
	while 1:
		n += 1
		msg = yield
		if n == 1:
			yield '1st: ' + msg
		elif n == 2:
			context.stream.send ('pre2nd: ' + msg)
			yield (
				'2nd: ' + msg,
				'post2nd: ' + msg
			)
		else:
			yield 'many: ' + msg

def onopenp (context):
  context.session.set ("WS_ID", context.stream.client_id)
  context.stream.send ("hi")

def onclosep (context):
  context.session.remove ("WS_ID")

@app.route ("/reporty")
@app.websocket (atila.WS_SESSION, 1200, onopenp, onclosep)
def reporty (context, message, a, b = '2', **payload):
	context.stream.send ("first message")
	return f'{a}: {message}'


@app.route ("/reporty/async")
@app.websocket (atila.WS_SESSION, 1200, onopenp, onclosep)
async def reporty_async (context, message, a, b = '2', **payload):
	context.stream.send ("first message")
	return f'{a}: {message}'


#--------------------------------------------------
import time


N = 0

@app.route ("/bench/chatty")
@app.websocket (atila.WS_CHATTY, 60)
def bench2 (context):
	global N
	while 1:
		msg = yield
		print (msg)
		yield f'echo: {msg}'
		N += 1; print (f"============== got messages: {N}")

@app.route ("/bench/session")
@app.websocket (atila.WS_SESSION, 60)
def bench3 (context, message):
	global N
	print (message)
	N += 1; print (f"============== got messages: {N}")
	return f'echo: {message}'

@app.route ("/bench/async")
@app.websocket (atila.WS_SESSION, 60)
async def bench4 (context, message):
	global N
	print (message)
	N += 1; print (f"============== got messages: {N}")
	return f'echo: {message}'

@app.route ("/bench/session_nopool")
@app.websocket (atila.WS_SESSION | atila.WS_OP_NOPOOL, 60)
def bench6 (context, message):
	global N
	print (message)
	N += 1; print (f"============== got messages: {N}")
	return f'echo: {message}'

@app.route ("/bench/async_channel")
@app.websocket (atila.WS_STREAM, 60)
async def bench7 (context):
	global N
	while 1:
		m = await context.stream.receive ()
		if not m:
			break
		N += 1; print (f"============== got messages: {N}")
		context.stream.send ('echo: ' + m)

@app.route ("/bench/N")
def bench_result (context):
	global N
	return str (N)


if __name__ == "__main__":
	import skitai

	skitai.enable_async ()
	skitai.mount ("/websocket", app)
	skitai.run (port = 30371)
