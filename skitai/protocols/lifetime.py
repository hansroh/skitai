import sys, time
from rs4 import asyncore
import gc
import select
import os
import bisect
import socket
import time
import types
from .sock.impl.dns import dns
from collections import deque
import threading

try:
	from pympler import muppy, summary, tracker
except ImportError:
	pass

if os.name == "nt":
	from errno import WSAENOTSOCK

_shutdown_phase = 0
_shutdown_timeout = 30 # seconds per phase
_exit_code = 0
_last_maintern = 0
_maintern_interval = 3.0
_killed_zombies = 0
_select_errors = 0
_poll_count = 0
_polling = 0
_logger = None

EXHAUST_DNS = True

class TickTimer:
	def __init__ (self):
		self.onces = []
		self._canceled = {}
		self._call_id = 0
		self._lock = threading.Lock ()

	def next (self, func, args = (), kargs = {}):
		return self.at (-1, func, args, kargs)

	def later (self, delay, func, args = (), kargs = {}):
		return self.at (time.monotonic () + delay, func, args, kargs)

	def at (self, at, func, args = (), kargs = {}):
		# at is time.monotonic ()
		with self._lock:
			self._call_id += 1
			call_id = self._call_id
			if at == -1:
				self.onces.insert (0, (time.monotonic (), call_id, func, args, kargs))
				return call_id
			# need to sort base
			last_at = self.onces and self.onces [-1][0] or None
			self.onces.append ((at, call_id, func, args, kargs))
			if last_at and at < last_at:
				self.onces.sort (key = lambda x: x [0])
		return call_id

	def cancel (self, call_id):
		with self._lock:
			self._canceled [call_id] = None

	def __len__ (self):
		with self._lock:
			return len (self.onces)

	def tick (self):
		now = time.monotonic ()
		funcs = []
		with self._lock:
			for i in range (len (self.onces)):
				at = self.onces [0][0]
				if at > now:
					break
				at, call_id, func, args, kargs = self.onces.pop (0)
				if call_id in self._canceled:
					self._canceled.pop (call_id)
					continue
				funcs.append ((func, args, kargs))

		for func, args, kargs in funcs:
			func (*args, **kargs)


class Maintern:
	def __init__ (self):
		self.q = []

	# mainternacing -----------------------------------------
	def sched (self, interval, func, args = None):
		now = time.time ()
		self.q.append ((now + interval, interval, func, args))
		self.q.sort (key = lambda x: x [0])
		#bisect.insort (self.q, (now + interval, interval, func, args))

	def __call__ (self, now):
		excutes = 0
		for exetime, interval, func, args in self.q:
			if exetime > now: break
			excutes += 1
			if args:
				func (now, *args)
			else:
				func (now)

		for i in range (excutes):
			exetime, interval, func, args = self.q.pop (0)
			#bisect.insort (self.q, (now + interval, interval, func, args))
			self.q.append ((now + interval, interval, func, args))
			self.q.sort (key = lambda x: x [0])

def maintern_gc (now):
	gc.collect ()

def maintern_zombie_channel (now, map = None):
	global _killed_zombies

	if map is None:
		map = asyncore.socket_map

	zombies = []
	for channel in map.values():
		if hasattr (channel, "handle_timeout"):
			try:
				# +3 is make gap between server & client
				iszombie = (now - channel.event_time) > channel.zombie_timeout
			except AttributeError:
				continue
			if iszombie:
				zombies.append (channel)

	for channel in zombies:
		_killed_zombies += 1
		try:
			channel.handle_timeout ()
		except:
			channel.handle_error ()

maintern = None
tick_timer = None
def init (kill_zombie_interval = 10.0, logger = None):
	global tick_timer, maintern, _logger

	_logger = logger
	maintern = Maintern ()
	maintern.sched (kill_zombie_interval, maintern_zombie_channel)
	maintern.sched (300.0, maintern_gc)
	tick_timer = TickTimer ()

summary_tracker = None
def summary_track (now):
	global summary_tracker

	all_objects = muppy.get_objects ()
	#all_objects = muppy.filter (all_objects, Type = dict)
	#for each in all_objects:
	#	print (each)
	sum1 = summary.summarize (all_objects)
	summary.print_ (sum1)
	print ('-' * 79)
	if summary_tracker is None:
		summary_tracker = tracker.SummaryTracker ()
	summary_tracker.print_diff ()

def enable_memory_track (interval = 10.0):
	global maintern
	maintern.sched (interval, summary_track)

def shutdown (exit_code, shutdown_timeout = 30.0):
	global _shutdown_phase
	global _shutdown_timeout
	global _exit_code

	if _shutdown_phase:
		# aready entered
		return

	if _shutdown_phase == 0:
		_exit_code = exit_code
		_shutdown_phase = 1

	_shutdown_timeout = shutdown_timeout

def loop (timeout = 30.0):
	global _shutdown_phase
	global _shutdown_timeout
	global _exit_code
	global _polling
	global maintern

	if maintern is None:
		init ()

	_shutdown_phase = 0
	_shutdown_timeout = 30
	_exit_code = 0
	_polling = 1

	try:
		lifetime_loop(timeout)
	except KeyboardInterrupt:
		graceful_shutdown_loop()
	else:
		graceful_shutdown_loop()

	_polling = 0

def remove_notsocks (map):
	global _select_errors, _logger

	# on Windows we can get WSAENOTSOCK if the client
	# rapidly connect and disconnects
	killed = 0
	for fd, obj in map.items():
		r = []; w = []; e = []
		is_r = obj.readable()
		is_w = obj.writable()
		if is_r:
			r = [fd]
		# accepting sockets should not be writable
		if is_w and not obj.accepting:
			w = [fd]
		if is_r or is_w:
			e = [fd]

		try:
			select.select (r, w, e, 0)

		except:
			#_logger and _logger.trace ()
			killed += 1
			_select_errors += 1

			try:
				try: obj.handle_expt ()
				except: obj.handle_error ()
			except:
				_logger and _logger.trace ()

			try: del map [fd]
			except KeyError: pass

	return killed

poll_fun = asyncore.poll

def poll_fun_wrap (timeout, map = None):
	global _logger, poll_fun

	map = map or asyncore.socket_map
	if EXHAUST_DNS:
		dns.pop_all ()

	try:
		poll_fun (timeout, map)

	except (SystemError, KeyboardInterrupt):
		raise

	except (TypeError, OSError) as why:
		_logger and _logger.trace ()
		killed = remove_notsocks (map) # WSAENOTSOCK
		if not killed:
			# no errors, restart worker
			raise

	except ValueError:
		_logger and _logger.trace ()
		# negative file descriptor, testing all sockets
		# or too many file descriptors in select(), divide and conquer
		if not remove_notsocks (map):
			half = int (len (map) / 2)
			tmap = {}
			cc = 0
			for k, v in map.items ():
				tmap [k] = v
				cc += 1
				if cc == half:
					poll_fun_wrap (timeout, tmap)
					tmap = {}
			poll_fun_wrap (timeout, tmap)

	except:
		_logger and _logger.trace ()
		raise


def lifetime_loop (timeout = 30.0, count = 0):
	global _last_maintern
	global _maintern_interval
	global tick_timer

	loop = 0
	map = asyncore.socket_map

	while map and _shutdown_phase == 0:
		poll_fun_wrap (timeout, map)
		tick_timer and tick_timer.tick ()
		now = time.time ()
		if (now - _last_maintern) > _maintern_interval:
			maintern (now)
			_last_maintern = now
		loop += 1
		if count and loop > count:
			break

def graceful_shutdown_loop ():
	global _shutdown_phase
	global tick_timer

	timestamp = time.time()
	timeout = 1.0
	map = asyncore.socket_map
	while map and _shutdown_phase < 4:
		time_in_this_phase = time.time() - timestamp
		veto = 0
		for fd,obj in map.items():
			try:
				fn = getattr (obj,'clean_shutdown_control')
			except AttributeError:
				pass
			else:
				try:
					veto = veto or fn (_shutdown_phase, time_in_this_phase)
				except:
					obj.handle_error()

		if veto and time_in_this_phase < _shutdown_timeout:
			poll_fun_wrap (timeout, map)
			tick_timer.tick ()
		else:
			_shutdown_phase += 1
			timestamp = time.time()
