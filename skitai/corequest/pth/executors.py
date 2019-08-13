import multiprocessing
import rs4
from rs4.logger import screen_logger
import time
from .task import Task

N_CPU = multiprocessing.cpu_count()

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
        wrap = Task (future, "{}.{}".format (f.__module__, f.__name__))
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

        