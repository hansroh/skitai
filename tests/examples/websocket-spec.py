from atila import Atila
import skitai
import atila

app = Atila (__name__)

app.access_control_allow_origin = ["*"]
app.debug = True
app.use_reloader = True
app.securekey = 'asdadada'

@app.route ("/coroutine")
@app.websocket (atila.WS_CHANNEL, 60)
def echo_coroutine (context):
	n = 0
	while 1:
		msg = yield context.Input ()
		if not msg:
			break
		yield 'echo: ' + msg
		n += 1
		if n % 3 == 0:
			yield 'double echo: ' + msg


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
			context.websocket.send ('pre2nd: ' + msg)
			yield (
				'2nd: ' + msg,
				'post2nd: ' + msg
			)
		else:
			yield 'many: ' + msg

def onopenp (context):
  context.session.set ("WS_ID", context.websocket.client_id)
  context.websocket.send ("hi")

def onclosep (context):
  context.session.remove ("WS_ID")

@app.route ("/reporty")
@app.websocket (atila.WS_SESSION, 1200, onopenp, onclosep)
def reporty (context, message, a, b = '2', **payload):
	context.websocket.send ("first message")
	return f'{a}: {message}'


@app.route ("/reporty/async")
@app.websocket (atila.WS_SESSION, 1200, onopenp, onclosep)
async def reporty_async (context, message, a, b = '2', **payload):
	context.websocket.send ("first message")
	return f'{a}: {message}'


#--------------------------------------------------
import time


N = 0

@app.route ("/bench/channel")
@app.websocket (atila.WS_CHANNEL, 60)
def bench1 (context):
	global N
	while 1:
		msg = yield context.read_input_stream ()
		if not msg:
			break
		print (msg)
		N += 1; print (f"============== got messages: {N}")
		yield f'echo: {msg}'

@app.route ("/bench/channelt")
@app.websocket (atila.WS_CHANNEL, 60)
def bench1_1 (context):
	def on_input (context, m):
		global N
		print (m)
		N += 1; print (f"============== got messages: {N}")
		yield f'echo: {m}'

	outstrm = context.create_output_stream (on_input)
	while 1:
		msg = yield context.read_input_stream ()
		yield outstrm.emit (msg)

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

@app.route ("/bench/N")
def bench_result (context):
	global N
	return str (N)


if __name__ == "__main__":
	import skitai

	skitai.enable_async ()
	skitai.mount ("/websocket", app)
	skitai.run (port = 30371)
