from atila import Atila
try:
    from services import route_guide_pb2
except ImportError:
    from services import route_guide_pb2_v3 as route_guide_pb2
import time
import atila

app = Atila (__name__)
app.debug = True
app.use_reloader = True

@app.route ("/routeguide.RouteGuide/RouteChat", input_stream = True)
def RouteChat (context):
	class InputHandler:
		def __init__ (self):
			self.prev_notes = []

		def __call__ (self, was, new_note):
			time.sleep (0.5)
			for prev_note in self.prev_notes:
				if prev_note.location == new_note.location:
					yield prev_note
			self.prev_notes.append (new_note)

	outstrm = context.create_output_stream (InputHandler ())
	while 1:
		new_note = yield context.read_input_stream ()
		yield outstrm.emit (new_note)


@app.route ("/websocket", input_stream = True)
@app.websocket (atila.WS_CHANNEL, 60)
def echo_coroutine (context):
	n = 0
	while 1:
		msg = yield context.read_input_stream ()
		if not msg:
			break
		yield 'echo: ' + msg
		n += 1
		if n % 3 == 0:
			yield 'double echo: ' + msg

@app.route ("/websocket/thread", input_stream = True)
@app.websocket (atila.WS_CHANNEL, 60)
def echo_coroutine_thread (context):
	class InputHandler:
		def __init__ (self):
			self.n = 0

		def __call__ (self, was, msg):
			self.n += 1
			yield 'echo: ' + msg
			if self.n % 3 == 0:
				yield 'double echo: ' + msg

	import threading
	outstrm = context.create_output_stream (InputHandler ())
	n = 0
	while 1:
		msg = yield context.read_input_stream ()
		yield outstrm.emit (msg)


if __name__ == "__main__":
	import skitai
	skitai.mount ("/", app)
	skitai.run (
		address = "0.0.0.0",
		port = 30371
	)
