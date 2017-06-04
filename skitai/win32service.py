import os
import sys
import win32serviceutil
import win32service
import win32event
import win32process
import pywintypes
import time
import os
import sys
import signal

BACKOFF_MAX = 300
BACKOFF_CLEAR_TIME = 30
BACKOFF_INITIAL_INTERVAL = 5

class ServiceFramework (win32serviceutil.ServiceFramework):
	_svc_name_ = "SAE_EXAMPLE"
	_svc_display_name_ = "SAE_EXAMPLE"
	_svc_app_ = r"D:\apps\skitai\examples\app.py"
	_svc_python_ = r"c:\python34\python.exe"
	
	def __init__(self, args):
		win32serviceutil.ServiceFramework.__init__(self, args)
		self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)		
		self.makeEnvirion ()			
	
	def makeEnvirion (self):
		self.cmd = "%s %s" % (self._svc_python_, self._svc_app_)		
		
	def createProcess(self, cmd):
		info  = win32process.CreateProcess(None, cmd, None, None, 0, win32process.CREATE_NEW_PROCESS_GROUP, None, None, win32process.STARTUPINFO())
		return info	
	
	def SvcStop(self):
		self.ReportServiceStatus (win32service.SERVICE_STOP_PENDING)
		os.kill (self.pid, signal.CTRL_C_EVENT)
		win32event.SetEvent(self.hWaitStop)

	def SvcDoRun(self):		
		cmd = self.cmd
		backoff_interval = BACKOFF_INITIAL_INTERVAL
		backoff_cumulative = 0

		import servicemanager
		servicemanager.LogMsg(
			servicemanager.EVENTLOG_INFORMATION_TYPE,
			servicemanager.PYS_SERVICE_STARTED,
			(self._svc_name_, ' (%s)' % self._svc_display_name_))
		
		while 1:			
			start_time = time.time()
			info = self.createProcess(cmd)
			self.hZope = info[0]
			self.pid = info[2]
			if backoff_interval > BACKOFF_INITIAL_INTERVAL:
				servicemanager.LogInfoMsg(
					'%s (%s): recovering from died process, new process '
					'started' % (self._svc_name_, self._svc_display_name_)
					)
			rc = win32event.WaitForMultipleObjects(
				(self.hWaitStop, self.hZope), 0, win32event.INFINITE)
				
			if rc == win32event.WAIT_OBJECT_0:
				self.SvcStop()
				break
				
			else:
				status = win32process.GetExitCodeProcess(self.hZope)				
				if status == 0:
					break
					
				else:
					if backoff_cumulative > BACKOFF_MAX:
						servicemanager.LogErrorMsg(
						  '%s (%s): process could not be restarted due to max '
						  'restart attempts exceeded' % (
							self._svc_display_name_, self._svc_name_
						  ))
						self.SvcStop()
						break
						
					servicemanager.LogWarningMsg(
					   '%s (%s): process died unexpectedly.  Will attempt '
					   'restart after %s seconds.' % (
							self._svc_name_, self._svc_display_name_,
							backoff_interval
							)
					   )
					   
					if time.time() - start_time > BACKOFF_CLEAR_TIME:
						backoff_interval = BACKOFF_INITIAL_INTERVAL
						backoff_cumulative = 0
					time.sleep(backoff_interval)
					backoff_cumulative = backoff_cumulative + backoff_interval
					backoff_interval = backoff_interval * 2

		servicemanager.LogMsg(
			servicemanager.EVENTLOG_INFORMATION_TYPE, 
			servicemanager.PYS_SERVICE_STOPPED,
			(self._svc_name_, ' (%s) ' % self._svc_display_name_))

	
if __name__=='__main__':	
	win32serviceutil.HandleCommandLine(ServiceFramework)
	
	