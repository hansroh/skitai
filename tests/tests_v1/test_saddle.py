from confutil import rprint, assert_request
import confutil
import jinja2
import os

def test_saddle (wasc, app):			
	was = wasc ()
	was.app = app
	app.skito_jinja ()
	app.set_home (confutil.getroot ())	
	assert app.get_resource () == os.path.join (confutil.getroot (), 'resources')
	app.watch (confutil)
	assert confutil in app.reloadables

def test_with_resource (wasc, app):
	@app.route ("/")
	def index (was):
		return 128		
	assert index (wasc ()) == 128
	
def test_events (wasc, app):
	@app.on ("pytest:event")
	def a (was):
		app.storage.set ("a", 256)
	
	@app.route ("/")
	def b	(was):
		was.app.emit ("pytest:event")
		return app.storage.get ("a")
		
	was = wasc ()
	was.app = app
	assert b (was) == 256
	
def test_broadcast (wasc, app):			
	was = wasc ()
	was.app = app

def test_resource_decorators (wasc, app):			
	was = wasc ()
	was.app = app

def test_app_decorators (wasc, app):			
	was = wasc ()
	was.app = app

def test_error_template (wasc, app):			
	was = wasc ()
	was.app = app
		
		
	