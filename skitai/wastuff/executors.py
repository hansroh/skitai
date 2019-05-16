import multiprocessing
import rs4
from concurrent.futures import TimeoutError
from rs4.logger import screen_logger
import time
from ..corequest.tasks import Mask
from skitai import was
from aquests.athreads import trigger
import sys

N_CPU = multiprocessing.cpu_count()

class Future:
    def __init__ (self, future, func):
        self.future = future
        self._name = "{}.{}".format (func.__module__, func.__name__)
        self._started = time.time ()
        self._was = None
        self.fulfilled = None

    def __str__ (self):
        return self._name

    def __getattr__ (self, name):
        return getattr (self.future, name)

    def _settle (self):
        expt, result = self.future.exception (0), None
        if self.fulfilled:
            if not expt:
                result = self.future.result (0)
            task = Mask (result, expt)
            try:
                self.fulfilled (self._was, task)
            except:
                self._was.traceback ()        
                trigger.wakeup (lambda p = self._was.response, d = self._was.app.debug and sys.exc_info () or None: (p.error (500, "Internal Server Error", d), p.done ()) )
            else:
                trigger.wakeup (lambda p = self._was.response: (p.done (),))
        elif expt:
            raise expt

    def asac (self, returning):
        # as soon as created
        return returning

    def then (self, func):
        self.fulfilled = func
        try: 
            self._was = was._clone ()
        except TypeError:
            pass
        return self


class Executor:
    def __init__ (self, executor_class, workers = None, zombie_timeout = None, logger = None):
        self._executor_class = executor_class 
        self._name = self._executor_class.__name__       
        self.logger = logger
        self.workers = workers or N_CPU
        self.zombie_timeout = zombie_timeout or (3600 * 24)
        self.lock = multiprocessing.Lock ()
        self.executor = None
        self.futures = []

    def __len__ (self):
        with self.lock:
            return len (self.futures)

    def maintern (self):
        now = time.time ()
        with self.lock:
            inprogresses = []
            for future in self.futures:                
                if not future.done ():
                     if future._started + self.zombie_timeout < now:
                         self.kill (future)
                     else:                             
                        inprogresses.append (future)       
                        continue                                            
                try:
                    future._settle ()
                except:
                    self.logger.trace (future._name)
            self.futures = inprogresses

    def create_excutor (self):
        self.executor = self._executor_class (self.workers)

    def shutdown (self):
        if not self.executor:
            return

        with self.lock:
            for future in self.futures:
                if not future.done ():
                    self.kill (future)
                elif not future.running ():
                    future.cancel ()                  

        self.executor.shutdown (wait = True)        
        self.maintern ()
        self.executor = None
        return len (self.futures)

    def kill (self, future):
        try:    
            future.result (timeout = 0)
        except TimeoutError:
            future.set_exception (TimeoutError)
            self.logger ("killed {}: {}".format (self._name, future))            
        
    def __call__ (self, f, *a, **b):    
        if self.executor is None:
            self.create_excutor ()
        else:
            self.maintern ()
        future = self.executor.submit (f, *a, **b)
        wrap = Future (future, f)
        self.logger ("started {}: {}".format (self._name, wrap))
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

        