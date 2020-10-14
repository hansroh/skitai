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
from ..wastuff import _WASType
from aquests.protocols.ws.collector import encode_message
from aquests.protocols.ws import *
from ..backbone.lifetime import tick_timer

WAS_FACTORY = None


class Coroutine:
    def __init__ (self, coro, was_id, resp_status = '200 OK'):
        self.coro = coro
        self.resp_status = resp_status
        self.producer = None
        self.contents = []
        self.input_streams = []
        self._was = None
        self._waiting_input = False
        self._rtype = None
        self._clone_and_deceive_was (was_id)
        self._determine_response_type ()

    def _clone_and_deceive_was (self, was_id):
        self._was = get_cloned_was (was_id)
        for n, v in self.coro.gi_frame.f_locals.items ():
            if not isinstance (v, _WASType):
                continue
            self.coro.gi_frame.f_locals [n] = self._was
        ctypes.pythonapi.PyFrame_LocalsToFast(ctypes.py_object (self.coro.gi_frame), ctypes.c_int (0))

    def _determine_response_type (self):
        if self._was.request.get_header ("upgrade") == 'websocket':
            self._rtype = 'websocket'
            self.resp_status = "101 Web Socket Protocol Handshake"
        elif self._was.request.get_header ("content-type", "").startswith ('application/grpc'):
            self._rtype = 'grpc'

    def serialize (self, v):
        if v is None:
            return
        if self._rtype is None:
            return v
        if self._rtype == 'grpc':
            return serialize (v, True)
        if self._rtype == 'websocket':
            return encode_message (v, OPCODE_TEXT if isinstance (v, str) else OPCODE_BINARY)

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

    def deallocate (self):
        # clean home
        if self._was is None:
            return
        deallocate_was (self._was)
        self._was = None
        self.input_streams = []
        self._waiting_input = False

    def close (self, data = None):
        data = self.serialize (data)
        if self.producer:
            if isinstance (data, (str, bytes)):
                self.producer.send (data)
                data = None
            self.producer.close ()
            self.deallocate ()
        return data

    def on_completed (self, was, task):
        while 1:
            try:
                try:
                    next_task = self.coro.send (task.fetch () if hasattr (task, 'set_proxy_coroutine') else task)
                except StopIteration as e:
                    return self.close (e.value)
                self._waiting_input = False

                if hasattr (next_task, 'set_proxy_coroutine'):
                    self._waiting_input = True
                    # 2nd loop entry point
                    self.input_streams and tick_timer.next (self.on_completed, (self._was, self.input_streams.pop (0)))
                    # self.input_streams and self.on_completed (self._was, self.input_streams.pop (0))
                    return

                if not isinstance (next_task, corequest):
                    next_task = self.serialize (next_task)
                    assert isinstance (next_task, (str, bytes, bytearray)), "str or bytes object required"
                    self.contents.append (next_task.encode () if isinstance (next_task, str) else next_task)

                    next_task = self.collect_data ()
                    if not self.producer:
                        if next_task is None:
                            return b''.join (self.contents)
                        if not hasattr (next_task, 'set_proxy_coroutine'):
                            callback = lambda x = next_task.then, y = (self.on_completed, self._was): x (*y)
                        else:
                            callback = None
                        self.producer = producers.sendable_producer (b''.join (self.contents), callback)
                        self.contents = []
                        return self.producer

                    else:
                        self.producer.send (b''.join (self.contents))
                        self.contents = []

            except:
                dinfo = '\n\n>>>>>>\nserver error occurred while processing your request\n\n'
                if self._was.app.debug:
                    dinfo += catch ()
                self.close (dinfo)
                raise

            if next_task:
                if hasattr (next_task, 'set_proxy_coroutine'):
                    self._waiting_input = True
                    # 3rd loop entry point
                    self.input_streams and tick_timer.next (self.on_completed, (self._was, self.input_streams.pop (0)))
                    # self.input_streams and self.on_completed (self._was, self.input_streams.pop (0))
                    return

                return next_task if hasattr (next_task, "_single") else next_task.then (self.on_completed, self._was)

    def collect_incomming_stream (self):
        while 1:
            collector = yield
            self.input_streams.append (collector)
            if self._waiting_input and self._was:
                # initial loop entry point
                self.on_completed (self._was, self.input_streams.pop (0))

    def start (self):
        from .tasks import Revoke

        task = self.collect_data ()
        if task is None:
            return b''.join (self.contents)
        if not isinstance (task, corequest):
            return task

        if hasattr (task, 'set_proxy_coroutine'):
            proxy = self.collect_incomming_stream ()
            next (proxy)
            task.set_proxy_coroutine (proxy)
            self._waiting_input = True # must next task.set_proxy_coroutine
            self.producer = producers.sendable_producer (b'')
            self._was.response.set_status (self.resp_status)
            return self.producer

        return task if hasattr (task, "_single") else task.then (self.on_completed, self._was)


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
