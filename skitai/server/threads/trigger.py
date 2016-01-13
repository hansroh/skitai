import asyncore
import socket
from .select_trigger import trigger

the_trigger = None

def start_trigger ():
	global the_trigger
	if the_trigger is None:
		the_trigger = trigger ()

def wakeup (thunk = None):
	global the_trigger
	
	if the_trigger is None:
		if thunk:
			try:
				thunk ()
			except:
				(file, fun, line), t, v, tbinfo = asyncore.compact_traceback()
		return		
			
	try:
		the_trigger.pull_trigger(thunk)
	except OSError as why:
		if why.errno == 32:
			the_trigger.close ()
			the_trigger = trigger ()
			the_trigger.pull_trigger(thunk)
	except socket.error:
		the_trigger.close ()
		the_trigger = trigger ()
		the_trigger.pull_trigger(thunk)
			
def wakeselect ():
	for fd, obj in list(asyncore.socket_map.items()):
		if hasattr(obj, "pull_trigger"):
			obj.pull_trigger()
