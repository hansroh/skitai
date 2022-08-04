from confutil import rprint
import confutil
import jinja2
import os
import time

def test_atila (Context, app):
	was = Context ()
	was.app = app
	app.skito_jinja ()
	app.set_home (confutil.getroot ())
	assert app.get_resource () == os.path.join (confutil.getroot (), 'resources')
	app._mount (confutil)
	assert confutil in app.reloadables

def test_with_resource (Context, app):
	@app.route ("/")
	def index (was):
		return 128
	assert index (Context ()) == 128

def test_events (Context, app):
	@app.on ("pytest:event")
	def a (was):
		app.store.set ("a", 256)

	@app.route ("/")
	def b	(was):
		was.app.emit ("pytest:event")
		return app.store.get ("a")

	was = Context ()
	was.app = app
	assert b (was) == 256

def test_broadcast (Context, app):
	was = Context ()
	was.app = app

def test_resource_decorators (Context, app):
	was = Context ()
	was.app = app

def test_app_decorators (Context, app):
	was = Context ()
	was.app = app

def test_error_template (Context, app):
	was = Context ()
	was.app = app
