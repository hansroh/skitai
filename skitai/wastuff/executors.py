import multiprocessing
import rs4
from concurrent.futures import TimeoutError, CancelledError
from rs4.logger import screen_logger
import time
from ..corequest.tasks import Mask
from skitai import was
from aquests.athreads import trigger
import sys

N_CPU = multiprocessing.cpu_count()

class Future:
    def __init__ (self, future, name):
        self.future = future
        self._name = name
        self._started = time.time ()
        self._was = None
        self._fulfilled = None

    def __str__ (self):
        return self._name

    def __getattr__ (self, name):
        return getattr (self.future, name)

    def _settle (self, future):
        expt, result = future.exception (0), None
        if self._fulfilled:
            if not expt:
                result = future.result (0)
            task = Mask (result, expt)            
            try:
                self._fulfilled (self._was, task)
            except:
                self._was.traceback ()        
                trigger.wakeup (lambda p = self._was.response, d = self._was.app.debug and sys.exc_info () or None: (p.error (500, "Internal Server Error", d), p.done ()) )
            else:
                trigger.wakeup (lambda p = self._was.response: (p.done (),))
            self._fulfilled = None

    def kill (self):
        try: self.future.result (timeout = 0)
        except: pass
        self.future.set_exception (TimeoutError)            

    def cancel (self):
        try: self.future.cancel ()
        except: pass
        self.future.set_exception (CancelledError) 

    def returning (self, returning):
        return returning

    def then (self, func):
        self._fulfilled = func
        try: self._was = was._clone (True)
        except TypeError: pass
        self.future.add_done_callback (self._settle)
        return self


class Executor:
    MAINTERN_INTERVAL = 30
    def __init__ (self, executor_class, workers = None, zombie_timeout = None, logger = None):
        self._executor_class = executor_class 
        self._name = self._executor_class.__name__       
        self.logger = logger
        self.workers = workers or N_CPU
        self.zombie_timeout = zombie_timeout
        self.last_maintern = time.time ()
        self.lock = multiprocessing.Lock ()
        self.executor = None
        self.futures = []

    def __len__ (self):
        with self.lock:
            return len (self.futures)

    def create_excutor (self):
        self.executor = self._executor_class (self.workers)

    def maintern (self, now):
        inprogresses = []
        for future in self.futures:                
            if future.done ():
                continue
            if self.zombie_timeout and future._started + self.zombie_timeout < now:
                future.kill ()
                self.logger ("zombie {} task is killed: {}".format (self._name, future))    
            else:
                inprogresses.append (future)       
                continue            
        self.futures = inprogresses

    def shutdown (self):
        if not self.executor:
            return
        with self.lock:
            for future in self.futures:
                if future.done ():
                    continue
                if not future.running ():
                    future.cancel ()
                    self.logger ("{} task is canceled: {}".format (self._name, future))            
                future.kill ()
                self.logger ("{} task is killed: {}".format (self._name, future))    
                
        self.executor.shutdown (wait = True)        
        with self.lock:
            self.maintern (time.time ())
            self.executor = None
            return len (self.futures)
    
    def __call__ (self, f, *a, **b):  
        with self.lock:
            if self.executor is None:
                self.create_excutor ()
            else:
                now = time.time ()
                if now > self.last_maintern + self.MAINTERN_INTERVAL:
                    self.maintern (time.time ())
        future = self.executor.submit (f, *a, **b)
        wrap = Future (future, "{}.{}".format (f.__module__, f.__name__))
        self.logger ("{} task started: {}".format (self._name, wrap))
        with self.lock:            
            self.futures.append (wrap)        
        return wrap


class Executors:
    def __init__ (self, workers = N_CPU, zombie_timeout = None, logger = None):
        self.logger = logger or screen_logger ()
        self.executors = [
            Executor (rs4.threading, workers, zombie_timeout, self.logger),
            Executor (rs4.processing, workers, zombie_timeout, self.logger)
        ]        
    
    def status (self):
        return dict (
            threads = len (self.executors [0]),
            processes = len (self.executors [1])
        )

    def cleanup (self):        
        return [e.shutdown () for e in self.executors]
    
    def create_thread (self, f, *a, **b):
        return self.executors [0] (f, *a, **b)

    def create_process (self, f, *a, **b):
        return self.executors [1] (f, *a, **b)

        