import threading
import sched, time, re
import bisect, sys, os
from skitai.lib  import confparse, logger as logger_module, processutil
import subprocess
import signal
import win32process, win32api, win32con, pywintypes
try:
	from urllib.request import urlopen
	from urllib.parse import urlparse
except ImportError:
	from urllib import urlopen	
	from urlparse import urlparse
	
import tempfile
				
class Scheduler (sched.scheduler):
	def __init__(self, wasc, config_path = None, logger = None, cache = 100):
		self.wasc = wasc
		self.logger = logger
		self.queue = []
		self.actions = {}
		self.jobs = {}
		self.timefunc = time.time
		self.delayfunc = time.sleep		
		self.active = 1
		self.supressed = 0
		self.supresstime = time.time ()
		self.config_path = config_path
		if not os.path.isfile (self.config_path):
			f = open (self.config_path, "w")
			f.write ("")
			f.close ()
		self.cv = threading.Condition (threading.RLock())
		self.mutate = 0
		self.run = 0
		self.log_path = tempfile.mkdtemp ()
		
		for each in self.logger.loggers:
			if isinstance (each, logger_module.rotate_logger):
				self.log_path = each.base
		
		if config_path:
			self.enter_from_config (config_path)
			
		f = threading.Thread (target = self.loop)
		f.setDaemon (1)
		f.start ()
	
	def makeBatchFile (self, batch, command):
		if os.name == "nt":
			shell_script_ext = ".cmd"	
		else:
			shell_script_ext = ".sh"
			
		instance_home = self.wasc.instance_home
		blade_home = self.wasc.blade_home
		blade_module = os.path.split (self.wasc.blade_home) [0]
		
		path = os.path.join (instance_home, "bin/%s%s" % (batch, shell_script_ext))
		env = (
			"REM @set PYTHONPATH=%%PYTHONPATH%%;%s\r\n"
			"REM @set BLADE_HOME=%s\r\n"
			"REM @set BLADE_INSTANCE_HOME=%s\r\n" % (blade_module, blade_home, instance_home)
		)		
		f = open (path, "w")
		f.write (env + command + " %1 %2 %3 %4 %5 %6 %7 %8 %9\r\n")		
		f.close ()
		
		return path
		
	def supress (self, sec = 30):
		self.supresstime = time.time () + sec
		self.supressed = 1
	
	def unsupress (self):
		self.supressed = 0	
		
	def mktime (self, date):
		date += [0, 0, 0]
		return time.mktime (tuple (date))
			
	def calculate (self, dates):		
		runtimes = []
		for date in dates.split (','):		
			week = -1
			current = self.timefunc()
			parsecurrent = time.localtime (current)			
			if date.find ("/") > -1:
				date, week = date.split ("/")
				try: week = int (week)
				except: week = -1
				if not (0 <= week < 7): 
					week = -1
			date = date.strip ()	
			parsedate = re.split ('\s+', date)
			
			if len (parsedate) < 3: continue
			for i in range (6 - len (parsedate)):
				parsedate.append ('0')
			
			wishdate = []
			for i in range (6):
				if parsedate [i] == '*':
					wishdate.append (parsecurrent [i])
				else:
					wishdate.append (int (parsedate [i]))
					
			nextrun = self.mktime (wishdate [:])
			
			# date control
			got_date = 0
			if nextrun > current:
				got_date = 1
			
			else:				
				for i in range (4, -1, -1):
					twishdate = wishdate [:]					
					if parsedate [i] == '*':
						twishdate [i] = twishdate [i] + 1
						nextrun = self.mktime (twishdate)
						if nextrun > current:
							wishdate = twishdate [:6]
							got_date = 1
							break
							
			if not got_date: return
			
			# date control
			date = time.localtime (self.mktime (wishdate [:3] + [0] * 3)) [:3]
			#apply recalculate date
			wishdate = list (date) + wishdate [3:]
			today = parsecurrent [:3]
			
			if date > today:
				for i in range (3):
					if date [i] != today [i]: break
						
				for j in range (4, i, -1):
					if parsedate [j] == '*':
						if j in (1, 2): wishdate [j] = 1
						else: wishdate [j] = 0
						
				nextrun = self.mktime (wishdate [:6])
			
			if week != -1:
				cweek = int (time.strftime ("%w", time.localtime (nextrun)))
				while week != cweek:
					nextrun += 3600 * 24
					cweek = int (time.strftime ("%w", time.localtime (nextrun)))
				
			runtimes.append (nextrun)
							
		if runtimes:
			runtimes.sort ()
			return runtimes [0]
	
	def enterabs (self, *event):
		bisect.insort(self.queue, event)
		return event
	
	def remove (self, job_id):
		self.cv.acquire ()
		self.mutate = 1
		queue = []
		for event in self.queue:
			if job_id == event [1]: continue
			bisect.insort (queue, event)
		self.queue = queue
		self.mutate = 0
		self.cv.notifyAll ()
		self.cv.release ()
	
	def enable (self, job_id, enable = 1, runafter = 0):		
		if job_id not in self.actions: return
		self.actions [job_id][-3] = enable
		self.renter (job_id, runafter)
			
	def renter (self, job_id, runafter = 0):
		if job_id not in self.actions: return		
		job_name, args, interval, date, enable, startat, timeouttokil = self.actions [job_id]
		self.enter (job_id, job_name, args, interval, date, enable, runafter, startat, timeouttokil)
		
	def enter (self, job_id, job_name, args, interval, date, enable = 1, runafter = 0, startat = "", timeouttokill = ""):
		try: timeouttokill = float (timeouttokill)
		except: timeouttokill = 0.	
		self.actions [job_id] = [job_name, args, interval, date, enable, startat, timeouttokill]
		self.remove (job_id)
		
		if runafter > 0:
			self.enterabs (self.timefunc() + (runafter * 60), job_id)
			return			
		
		nextrun = None		
		if date:
			nextrun = self.calculate (date)
			if interval:
				self.actions [job_id][3] = None # first starting time and run with interval
		elif interval:
			nextrun  = self.timefunc() + (interval * 60)
			
		if nextrun:
			self.enterabs (nextrun, job_id)
		else:
			self.actions [job_id] = self.actions [job_id][-3] = 0 # disable
			self.enterabs (sys.maxsize, job_id)
	
	RX_ENV = re.compile ("(%([_a-zA-Z]+)%)")
	def replace_env (self, text):
		for env, key in self.RX_ENV.findall (text):
			if os.environ.get (key, ""):
				text = text.replace (env, os.environ [key])
		return text
	
	def url_open (self, job_id, url, timeout):
		# Don't self https requesting!
		# I don't know why, but server will be hung up
		job_name = self.actions [job_id][0]
		self.logger ("[info] schedule %s started" % job_name)
		try:
			scheme, netloc, script, params, qs, fragment = urlparse (url)
			call = self.wasc.rcall.Server ("%s://%s" % (scheme, netloc))
			uri = script
			if params: uri += ";" + params
			if qs: uri += "?" + qs
			call.request (uri)
			self.jobs [job_id] = [None, None, 0, time.time ()]
			rs = call.getwait (timeout)
			self.logger ("[info] schedule %s result status: %s, http response code: %s" % (job_name, rs.status, rs.status == 1 and rs.code or -1))
		
		except:
			self.logger.trace (job_name)
		
		try:				
			del self.jobs [job_id]
		except KeyError:	
			pass
	
	def url_open2 (self, job_id, url, timeout):
		# Due to timeoputsocket, https will not work
		job_name = self.actions [job_id][0]
		self.logger ("[info] schedule %s started" % job_name)
		try:
			self.jobs [job_id] = [None, None, 0, time.time ()]
			rs = urlopen (url, timeout = timeout)			
			self.logger ("[info] schedule %s result status: %s %s" % (job_name, rs.code, rs.msg))		
		except:
			self.logger.trace (job_name)
		
		try:				
			del self.jobs [job_id]
		except KeyError:	
			pass
		
	def create_process (self, job_id, cmd, startat):
		job_name = self.actions [job_id][0]
		try:	
			dlogs = []
			for file in os.listdir (self.log_path):
				if file.find ("schedtask-%s-" % job_id) != 0: continue
				dlogs.append (file)	
			
			if len (dlogs) > 7:
				dlogs.sort ()
				for file in dlogs [:-7]:
					try: os.remove (os.path.join (self.log_path, file))
					except: pass
		
			output = os.path.join (self.log_path, "task-%s.log" % job_id)
			if os.path.isfile (output):
				rotate = open (os.path.join (self.log_path, "task-%s-%s.log" % (job_id, logger_module.now (0))), "a")
				olds = open (output)
				for line in olds:
					rotate.write (line)					
				olds.close ()
				rotate.close ()
			
			fh = open (output, "w")
			
			
				
			cmd = self.replace_env (cmd)
			if startat:
				cmdline = 'cmd.exe /C "cd /d %s && %s"' % (startat, cmd)
			else:	
				cmdline = 'cmd.exe /C "%s"' % cmd
				
			proc = subprocess.Popen (cmdline, stdout=fh, stderr=fh)
			
		except: 
			self.logger.trace ()
		
		else:		
			self.logger ("[info] schedule %s started" % job_name)
			self.jobs [job_id] = [proc, fh, 0, time.time ()]
	
	def isrunning (self, job_id):		
		if job_id not in self.jobs: return 0
		proc, fh, sizef, lastmodified = self.jobs [job_id]
		if proc:
			status = proc.poll ()
			if status is None: 
				return 1
			else:
				del self.jobs [job_id]
				if fh:
					fh.close()
				job_name = self.actions [job_id][0]
				self.logger ("[info] schedule %s terminated" % job_name)	
				return 0
		else:
			return 1 # maybe url request
	
	def kill (self, job_id):	
		if job_id not in self.jobs: 
			return 0, "", "no such job %s" % job_id
		job_name = self.actions [job_id][0]
		proc, fh, sizef, lastmodified = self.jobs [job_id]
		if proc is None: # url request
			return 0, "", "job %s is not a process" % job_name
			
		cpids = [proc.pid] + processutil.get_child_pid (proc.pid)
		cpids.reverse ()
		for cpid  in cpids:
			try:
				handle = win32api.OpenProcess (win32con.PROCESS_TERMINATE, 0, cpid)
				win32api.TerminateProcess (handle, 0)
				win32api.CloseHandle (handle)		
			except pywintypes.error as why:
				if why.errno == 87:
					pass
				else:	
					return why, "", "killing %s(pid:%d) has been failed" % (job_name, proc.pid)
		
		del self.jobs [job_id]
		if fh: fh.close()
		return 0, "", "%s(pid:%d) was killed" % (job_name, proc.pid)
	
	def maintern (self):	
		for job_id in list(self.jobs.keys ()):
			job_name = self.actions [job_id][0]
			lastmodified = self.jobs [job_id][-1]
			timeouttokill = self.actions [job_id][-1]
			if timeouttokill and time.time () - lastmodified > (timeouttokill * 60) and self.isrunning (job_id):
				self.logger ("[info] schedule %s was timeout, try to kill..., result: %s" % (job_name, self.kill (job_id)))
				
	def loop (self):
		while 1:
			self.run += 1
			if self.run % 10 == 0:
				self.maintern ()
			
			if not self.active or not self.queue:
				self.delayfunc(3)
				continue
			
			if self.supressed:
				if self.supresstime > time.time ():
					self.delayfunc(3)					
					continue
				else:
					self.supressed = 0	
			
			self.cv.acquire ()
			runnable = False
			while self.mutate: self.cv.wait ()			
			for i in range (len(self.queue)):
				sched, job_id = self.queue [i]
				if not self.isrunning (job_id):
					runnable = True
					break
			self.cv.release ()
			if not runnable:
				continue
					
			remain = sched - self.timefunc()			
			if remain > 0.:
				if remain <= 3.:
					self.delayfunc (remain)
				else:
					self.delayfunc (3)
				continue
			
			job_name, args, interval, date, enable, startat, timeouttokill = self.actions [job_id]			
			if enable:
				if args.startswith ("HTTP "):
					threading.Thread (target = self.url_open, args = (job_id, args[5:].strip (), timeouttokill)).start ()
				elif args.startswith ("SHELL "):
					self.create_process (job_id, args[6:].strip (), startat)
				else:
					self.create_process (job_id, args, startat)

			self.renter (job_id)
	
	def readoutput (self, job_id, char = 10000):
		fo = os.path.join (self.log_path, "task-%s.log" % job_id)
		if not os.path.isfile (fo): return []
		
		size = os.stat (fo).st_size		
		if job_id in self.jobs:		
			self.jobs [job_id][-2] = size
			self.jobs [job_id][-1] = time.time ()
					
		if size < char: pos = 0
		else: pos = size - char
		f = open (fo)
		f.seek (pos)		
		if pos > 0: f.readline ()		
		buffer = []
		while 1:
			t = f.readline ()
			if not t: return buffer
			buffer.append (t.strip ())
		f.close ()	
		return buffer

	def cancel (self):
		self.active = 0
	
	def start (self):
		self.active = 1
	
	def status (self):
		if not self.active:
			asctime = time.asctime (time.localtime (time.time ()))			
			return [('-1', 'All jobs stopped', '', 'Scheduler')]
		
		k = []
		for sched, job_id in self.queue:
			if job_id not in self.actions: continue
			job_name, args, interval, date, enable, startat, timeouttokill = self.actions [job_id]
			if sched == sys.maxsize:
				asctime = "Not Scheduled"
			else:
				asctime = time.asctime (time.localtime (sched))				
			
			if self.isrunning (job_id) and not enable:
				status = "be disabled"
			elif self.isrunning (job_id):
				status = "running"
			elif enable:
				status = "waiting"				
			else:
				status = "disabled"
				
			k.append ((job_id, job_name, asctime, status, args))
					
		return k
	
	def add_job (self, job_id):		
		job_name = self.config.getopt (job_id, 'name')
		args = self.config.getopt (job_id, 'args')		
		date = self.config.getopt (job_id, 'date')
		interval = self.config.getint (job_id, 'interval')
		enable = self.config.getint (job_id, 'enable')
		runafter = self.config.getint (job_id, 'runatstart')
		timeouttokill = self.config.getopt (job_id, 'timeouttokill')
		if timeouttokill is None: timeouttokill = ""
		startat = self.config.getopt (job_id, 'startat')
		if startat is None: startat = ""		
		self.enter (job_id, job_name, args, interval, date, enable, runafter, startat, timeouttokill)
		
	def enter_from_config (self, config_path):
		self.config = confparse.ConfParse (config_path)
		for job_id in list(self.config.keys ()):
			self.add_job (job_id)
		
	def remove_config (self, job_id):
		self.remove (job_id)
		
		if job_id in self.config:
			del self.config [job_id]
			self.config.update ()			
		
		try: del self.actions [job_id]	
		except KeyError: pass		
		
	valid_keys = ['name','args','date','interval','enable','runatstart','timeouttokill','startat']
	def new_config (self, job_id, dict):
		self.config.makesect (job_id)
		for k, v in list(dict.items ()):
			if k not in self.valid_keys: continue
			self.config.setopt (job_id, k, v)
		self.config.update ()
		self.add_job (job_id)
	
	def has_key (self, job_id):
		return job_id in self.config
	
	def get_config (self):
		return self.config
			
	def update_config (self, job_id, dict):
		for k, v in list(dict.items ()):
			if k not in self.valid_keys: continue
			self.config.setopt (job_id, k, v)
		self.config.update ()
		self.add_job (job_id)
		
	def cleanup (self):	
		self.active = 0		
		