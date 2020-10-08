from ..exceptions import HTTPError
from ..utility import make_pushables
import sys
from ..wastuff.api import API
import ctypes
import types
from rs4 import producers
from aquests.athreads import trigger

WAS_FACTORY = None

class Coroutine:
    def __init__ (self, coro):
        self.coro = coro
        self.was = None
        self.producer = None
        self.contents = []

    def collect_data (self):
        while 1:
            try:
                task = next (self.coro)
            except StopIteration as e:
                if e.value and isinstance (e.value, (str, bytes)):
                    self.contents.append (e.value.encode () if isinstance (e.value, str) else e.value)
                    return
                return e.value

            if isinstance (task, corequest):
                return task
            self.contents.append (task.encode () if isinstance (task, str) else task)

    def on_completed (self, was, task):
        if self.was is None:
            self.was = was # replacing to cloned was
            self.coro.gi_frame.f_locals ['was'] = was
            ctypes.pythonapi.PyFrame_LocalsToFast(ctypes.py_object (self.coro.gi_frame), ctypes.c_int (0))

        while 1:
            try:
                _task = self.coro.send (task)
            except StopIteration as e:
                if self.producer and isinstance (e.value, (str, bytes)):
                    self.producer.send (e.value)
                self.producer and self.producer.close ()
                return e.value

            if not isinstance (_task, corequest):
                assert isinstance (_task, (str, bytes)), "str or bytes object required"
                self.contents.append (_task.encode () if isinstance (_task, str) else _task)
                _task = self.collect_data ()
                if not self.producer:
                    if _task is None:
                        return b''.join (self.contents)
                    callback = lambda x = _task.then, y = (self.on_completed, was): x (*y)
                    self.producer = producers.sendable_producer (b''.join (self.contents), callback)
                    self.contents = []
                    return self.producer

                else:
                    self.producer.send (b''.join (self.contents))
                    self.contents = []
                    continue

            return _task if hasattr (_task, "_single") else _task.then (self.on_completed, was)

    def start (self):
        task = self.collect_data ()
        if task is None:
            return b''.join (self.contents)
        if not isinstance (task, corequest):
            return task
        return task if hasattr (task, "_single") else task.then (self.on_completed)


class CorequestError (Exception):
    pass


def get_cloned_was (was_id):
    global WAS_FACTORY

    assert was_id, 'was.ID should be non-zero'
    if WAS_FACTORY is None:
        from skitai import was
        WAS_FACTORY = was

    _was = WAS_FACTORY._get_by_id (was_id)
    assert hasattr (_was, 'app'), 'corequest future is available on only Atila'

    if isinstance (was_id, int): # origin
        return _was._clone ()
    return _was


class corequest:
    def _get_was (self):
        return get_cloned_was (self.meta ['__was_id'])

    def _late_respond (self, tasks_or_content):
        # NEED self._fulfilled and self._was
        if not hasattr (self._was, 'response'):
            # already responsed: SEE app2.map_in_thread
            return

        response = self._was.response
        try:
            if self._fulfilled == 'self':
                content = tasks_or_content.fetch ()
            else:
                content = self._fulfilled (self._was, tasks_or_content)
            self._fulfilled = None
        except MemoryError:
            raise
        except HTTPError as e:
            response.start_response (e.status)
            content = response.build_error_template (e.explain or (self._was.app.debug and e.exc_info), e.errno, was = self._was)
        except:
            self._was.traceback ()
            response.start_response ("502 Bad Gateway")
            content = response.build_error_template (self._was.app.debug and sys.exc_info () or None, 0, was = self._was)

        if isinstance (content, API) and self._was.env.get ('ATILA_SET_SEPC'):
            content.set_spec (self._was.app)

        will_be_push = make_pushables (response, content)
        if will_be_push is None:
            return # future

        try:
            for part in will_be_push:
                response.push (part)
            response.done ()

        finally:
            if not isinstance (content, producers.Sendable): # IMP: DO NOT release
                self.deallocate ()

    def deallocate (self):
        was = self._was
        was.apps = None
        was.env = None
        try: del was.response
        except AttributeError: pass
        try: del was.request
        except AttributeError: pass
        self._was = None

    # basic methods --------------------------------------
    def get_timeout (self):
        return self._timeout

    def set_timeout (self, timeout):
        self._timeout = timeout

    def returning (self, returning):
        # coreauest.then (callback).returning ("201 Created")
        return returning

    # implementables --------------------------------------
    def then (self, func, was):
        # usally return self and chaing with returning ()
        raise NotImplementedError

    def cache (self, cache = 60, cache_if = (200,)):
        raise NotImplementedError

    def dispatch (self, cache = None, cache_if = (200,), timeout = None):
        # response object with data
        raise NotImplementedError

    def wait (self, timeout = None):
        # response object without data
        raise NotImplementedError

    def commit (self, timeout = None):
        # return None. if error had been occured will be raised
        raise NotImplementedError

    def fetch (self, cache = None, cache_if = (200,), timeout = None):
        # return data. if error had been occured will be raised
        raise NotImplementedError

    def one (self, cache = None, cache_if = (200,), timeout = None):
        # return data with only one element. if error had been occured will be raised
        raise NotImplementedError


class response (corequest):
    pass
