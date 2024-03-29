import threading, time, sys
from skitai import lifetime
import threading
try:
	import queue
except ImportError:
	import Queue as queue
from collections import deque

class request_thread (threading.Thread):
	def __init__ (self, queue, logger, id = 0):
		threading.Thread.__init__ (self)
		self.queue = queue
		self.id = id
		self.logger = logger
		self.setDaemon (1)
		self.idle = 1
		self.command = ''
		self.exec_time = 0.
		self.lock = threading.Lock ()
		if id == 0:
			self.__exc_times = deque (maxlen = 32)
			self.avg_exc_times = 0.1

	def run (self):
		while 1:
			job = self.queue.get ()
			if job is None: break
			with self.lock:
				self.idle = 0
				self.command = str (job)

			start_time = time.time()
			try:
				job ()
			except MemoryError:
				self.logger.trace ("thread #%d" % self.id)
				lifetime.shutdown (1, 1.0)
			except:
				self.logger.trace ("thread #%d" % self.id)

			exc_time = time.time() - start_time
			with self.lock:
				self.exec_time = exc_time
				self.idle = 1

			if self.id == 0:
				self.__exc_times.append (exc_time)
				with self.lock:
					self.avg_exc_times = sum (self.__exc_times) / len (self.__exc_times)
			del job

	def getId (self):
		return self.id

	def status (self):
		self.lock.acquire ()
		idle = self.idle
		command = self.command
		exec_time = self.exec_time
		self.lock.release ()

		s = {
			"object_id": id (self),
			"thread_id": self.id,
			"status": idle and "IDLE" or "BUSY",
			"command":	command,
			"exec_time": "%d ms" % (exec_time * 1000,)
		}
		if self.id == 0:
			s ['avg_exc_times'] = self.avg_exc_times
		return s


class thread_pool:
	def __init__ (self, queue, child, logger):
		self.tpool = {}
		for i in range (child):
			d = request_thread (queue, logger, i)
			self.tpool [i] = d
			d.start ()

	def __len__ (self):
		return len (self.tpool)

	def __getitem__ (self, k):
		return self.tpool [k]

	def cleanup (self):
		pass

	def get_avg_exc_times (self):
		return self.tpool [0].avg_exc_times

	def status (self):
		d = {}
		for child_id, child in list(self.tpool.items()):
			d [child_id] = child.status ()
		return d


class request_queue:
	def __init__ (self):
		self.mon = threading.RLock()
		self.cv = threading.Condition (self.mon)
		self.queue = []

	def qsize (self):
		with self.mon:
			return len (self.queue)

	def put(self, item, prior = 0):
		with self.cv:
			if prior:
				self.queue.insert (0, item)
			else:
				self.queue.append (item)
			self.cv.notify ()

	def get (self):
		with self.cv:
			while not self.queue:
				self.cv.wait()
			item = self.queue.pop (0)
		return item

	def cleanup (self):
		with self.mon:
			self.queue = []

	def status(self):
		with self.mon:
			return {
				"qsize": len (self.queue),
				"in_queue": [str(x [1]) for x in self.queue]
			}


class request_queue2 (queue.Queue):
	def __init__(self, maxsize = 0):
		queue.Queue.__init__ (self, maxsize)
		self.maxq = 0

	def cleanup (self):
		while 1:
			try: item = self.get_nowait ()
			except queue.Empty: break
			del item

		for i in range (1024):
			self.put (None)

		while 1:
			try: self.get_nowait ()
			except queue.Empty: break

	def put(self, item, block=True, timeout=None):
		qsize = self.qsize ()
		with self.mutex:
			if qsize > self.maxq:
				self.maxq = qsize
		queue.Queue.put (self, item, block, timeout)

	def status(self):
		with self.mutex:
			qsize = len (self.queue)
			maxq = self.maxq

		return {
			"qsize": qsize,
			"max": maxq
		}
