import asyncore
import socket
from select_trigger import trigger

the_trigger = None

def start_trigger ():
	global the_trigger	
	the_trigger = trigger ()

def wakeup (thunk = None):
	global the_trigger
	try:
		the_trigger.pull_trigger(thunk)
	except OSError, why:
		if why[0] == 32:
			the_trigger.close ()
			the_trigger = trigger ()
			the_trigger.pull_trigger(thunk)
	except socket.error:
		the_trigger.close ()
		the_trigger = trigger ()
		the_trigger.pull_trigger(thunk)
			
def wakeselect ():
	for fd, obj in asyncore.socket_map.items():
		if hasattr(obj, "pull_trigger"):
			obj.pull_trigger()
			