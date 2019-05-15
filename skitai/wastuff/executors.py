import multiprocessing
import rs4
from concurrent.futures import TimeoutError
from rs4.logger import screen_logger
import time

N_CPU = multiprocessing.cpu_count()

class Future:
    def __init__ (self, future, func):
        self.future = future
        self._name = "{}.{}".format (func.__module__, func.__name__)
        self._started = time.time ()

    def then (self, r):
        return r

    def __str__ (self):
        return self._name

    def __getattr__ (self, name):
        return getattr (self.future, name)


class Executor:
    def __init__ (self, executor_class, workers = N_CPU, logger = None):
        self._executor_class = executor_class 
        self._name = self._executor_class.__name__       
        self.logger = logger
        self.workers = workers
        self.lock = multiprocessing.Lock ()
        self.executor = None
        self.futures = []

    def __len__ (self):
        with self.lock:
            return len (self.futures)

    def maintern (self):
        with self.lock:
            inprogresses = []
            for future in self.futures:
                if not future.done ():
                     inprogresses.append (future)       
                     continue
                expt = future.exception (0)
                if expt:
                    try:
                        raise expt
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
                    continue
                if not future.running ():
                    future.cancel ()
                    continue
                try:    
                    future.result (timeout = 3.0)
                except TimeoutError:
                    pass

        self.executor.shutdown (wait = True)
        self.maintern ()
        return len (self.futures)

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
    def __init__ (self, workers = N_CPU, logger = None):
        self.logger = logger or screen_logger ()
        self.executors = [
            Executor (rs4.threading, workers, self.logger),
            Executor (rs4.processing, workers, self.logger)
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

        