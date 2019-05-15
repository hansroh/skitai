import multiprocessing
import rs4
from concurrent.futures import TimeoutError, CancelledError
N_CPU = multiprocessing.cpu_count()

class Executor:
    def __init__ (self, executor_class, workers = N_CPU):
        self._executor_class = executor_class
        self.workers = workers
        self.lock = multiprocessing.Lock ()
        self.executor = None
        self.futures = []

    def __len__ (self):
        with self.lock:
            return len (self.futures)

    def maintern (self):
        with self.lock:             
            self.futures = [future for future in self.futures if not future.done ()]                

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

    def __call__ (self, f, *a, **b):     
        if self.executor is None:
            self.create_excutor ()
        else:
            self.maintern ()
        future = self.executor.submit (f, *a, **b)
        with self.lock:
            self.futures.append (future)
        return future, len (self.futures)


class Executors:
    def __init__ (self, workers = N_CPU):
        self.executors = [
            Executor (rs4.threading, workers),
            Executor (rs4.processing, workers)        
        ]
    
    def status (self):
        return dict (
            threads = len (self.executors [0]),
            processes = len (self.executors [1])
        )

    def cleanup (self):        
        [e.shutdown () for e in self.executors]
    
    def create_thread (self, f, *a, **b):
        return self.executors [0] (f, *a, **b)

    def create_process (self, f, *a, **b):
        return self.executors [1] (f, *a, **b)

        