from atila import Atila
import skitai
import atila
import asyncio

app = Atila (__name__)

app.access_control_allow_origin = ["*"]
app.debug = True
app.use_reloader = True
app.jinja_overlay ()
app.securekey = 'asdadada'

@app.route ("/echo-single")
def echo_single (context, message):
	# return a single message, use aquests.ws (DO NOT USE /echo)
	if context.wsinit ():
		return context.wsconfig (skitai.WS_CHANNEL, 60)
	elif context.wshasevent (): # ignore the other events
		return
	return "You said," + message

@app.route ("/echo")
def echo (context, message):
	if context.wsinit ():
		return context.wsconfig (skitai.WS_CHANNEL, 60)
	elif context.wsopened ():
		return "Welcome Client %s" % context.wsclient ()
	elif context.wshasevent (): # ignore the other events
		return

	context.stream.send ("You said," + message)
	context.stream.send ("acknowledge")

def onopen (context):
	return  'Welcome Client 0'

@app.route ("/echo2")
@app.websocket (skitai.WS_CHANNEL | skitai.WS_NOTHREAD, 60, onopen = onopen)
def echo2 (context, message):
	context.stream.send ('1st: ' + message)
	return "2nd: " + message

@app.route ("/echo3")
@app.websocket (skitai.WS_CHANNEL | skitai.WS_THREADSAFE, 60, onopen = onopen)
def echo3 (context, message):
	context.stream.send ('1st: ' + message)
	return "2nd: " + message

@app.route ("/echo4")
@app.websocket (skitai.WS_CHANNEL | skitai.WS_SESSION, 60)
def echo4 (context):
	n = 0
	while 1:
		n += 1
		msg = yield
		if n == 1:
			yield '1st: ' + msg
		elif n == 2:
			yield '2nd: ' + msg
		else:
			yield 'many: ' + msg

def onopenp (context):
  context.session.set ("WS_ID", context.stream.client_id)

def onclosep (context):
  context.session.remove ("WS_ID")

@app.route ("/push")
@app.websocket (skitai.WS_CHANNEL, 1200, onopenp, onclosep)
def push (context, message):
  return 'you said: ' + message

@app.route ("/wspush")
def ws_push (context):
	context.session.set ("WS_ID", 0)
	app.websocket_send (
      	context.session.get ("WS_ID"),
       "Item In Stock!"
	)
	return "Sent"

def onchatopen (context):
	return "Client %s has entered" % context.wsclient ()

def onchatclose (context):
	return "Client %s has leaved" % context.wsclient ()

@app.route ("/")
def websocket (context, mode = "echo"):
	if mode == "chat":
		mode += "?room_id=1"
	return context.render ("websocket.html", path = mode)

@app.route ("/echo_coroutine")
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

@app.route ("/echo_coroutine2")
@app.websocket (atila.WS_CHANNEL, 60)
def echo_coroutine2 (context):
	while 1:
		msg = yield context.Input ()
		if not msg:
			break

		task = yield context.Mask ('http://example.com')
		yield task.fetch ()


@app.route ("/param")
@app.websocket (skitai.WS_CHANNEL, 1200, onopenp, onclosep)
def param (context, message, a, b = '2', **payload):
  return 'you said: ' + message


@app.route ("/echo_async")
@app.websocket (atila.WS_STREAM, 60)
async def echo_async (context, a):
	while 1:
		m = await context.stream.receive ()
		if not m:
			break
		await context.stream.send ('echo: ' + m)


@app.route ("/echo_async_iter")
@app.websocket (atila.WS_STREAM, 60)
async def echo_async_iter (context, a):
	async for m in context.stream:
		yield 'echo: ' + m


if __name__ == "__main__":
	import skitai

	skitai.mount ("/websocket", app)
	skitai.run (port = 30371, tasks = 4)
