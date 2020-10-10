from ..exceptions import HTTPError
from ..utility import make_pushables
import sys
from ..wastuff.api import API
import ctypes
import types
from rs4 import producers
from aquests.athreads import trigger
from ..utility import deallocate_was, catch
from aquests.protocols.grpc.producers import serialize

WAS_FACTORY = None


class Coroutine:
    def __init__ (self, coro, was_id):
        self.coro = coro
        self.was = get_cloned_was (was_id)
        self.producer = None
        self.contents = []
        self.receiver = []
        self.coro.gi_frame.f_locals ['was'] = self.was
        ctypes.pythonapi.PyFrame_LocalsToFast(ctypes.py_object (self.coro.gi_frame), ctypes.c_int (0))

    def serialize (self, v):
        return serialize (v, True) if hasattr (v, 'SerializeToString') else v

    def collect_data (self):
        while 1:
            try:
                task = next (self.coro)
            except StopIteration as e:
                value = self.serialize (e.value)
                if value and isinstance (value, (str, bytes)):
                    self.contents.append (value.encode () if isinstance (value, str) else value)
                    return
                return value
            if isinstance (task, corequest):
                return task
            task = self.serialize (task)
            self.contents.append (task.encode () if isinstance (task, str) else task)

    def close (self, data = None):
        data = self.serialize (data)
        if self.producer:
            if isinstance (data, (str, bytes)):
                self.producer.send (data)
            self.producer.close ()
            deallocate_was (self.was)
            self.was = None
            return
        return data

    def on_completed (self, was, task):
        while 1:
            try:
                try:
                    _task = self.coro.send (task)
                except StopIteration as e:
                    return self.close (e.value)
                if not isinstance (_task, corequest):
                    _task = self.serialize (_task)
                    assert isinstance (_task, (str, bytes)), "str or bytes object required"
                    self.contents.append (_task.encode () if isinstance (_task, str) else _task)
                    _task = self.collect_data ()
                    if not self.producer:
                        if _task is None:
                            return b''.join (self.contents)
                        callback = lambda x = _task.then, y = (self.on_completed, self.was): x (*y)
                        self.producer = producers.sendable_producer (b''.join (self.contents), callback)
                        self.contents = []
                        return self.producer

                    else:
                        self.producer.send (b''.join (self.contents))
                        self.contents = []

            except:
                dinfo = '\n\n>>>>>>\nserver error occurred while processing your request\n\n'
                if self.was.app.debug:
                    dinfo += catch ()
                self.close (dinfo)
                raise

            if _task:
                return _task if hasattr (_task, "_single") else _task.then (self.on_completed, self.was)

    def start (self):
        task = self.collect_data ()
        if task is None:
            return b''.join (self.contents)
        if not isinstance (task, corequest):
            return task
        return task if hasattr (task, "_single") else task.then (self.on_completed, self.was)


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
            dinfo = self._was.app.debug and sys.exc_info () or None
            content = response.build_error_template (dinfo, 0, was = self._was)

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
                deallocate_was (self._was)
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
