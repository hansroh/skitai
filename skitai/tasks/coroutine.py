from skitai.exceptions import HTTPError
import sys
from skitai.wastuff.api import API
import ctypes
from rs4.misc import producers
from skitai.utility import deallocate_was
from rs4.protocols.sock.impl.grpc.producers import serialize
from rs4.protocols.sock.impl.ws.collector import encode_message
from rs4.protocols.sock.impl.ws import *
from skitai.backbone.lifetime import tick_timer
from . import Coroutine, Task
from . import utils

class Coroutine (Coroutine):
    def __init__ (self, was, coro, request_postprocessing, resp_status = '200 OK'):
        self.coro = coro
        self.resp_status = resp_status
        self.producer = None
        self.contents = []
        self.input_streams = []
        self._was = None
        self._waiting_input = False
        self._rtype = None
        self._clone_and_deceive_context (was.ID, request_postprocessing)
        self._determine_response_type ()

    def _clone_and_deceive_context (self, was_id, request_postprocessing):
        from skitai.wsgiappservice.wastype import _WASType

        self._was = utils.get_cloned_context (was_id)
        self._was.request.postprocessing = request_postprocessing

        for n, v in self.coro.gi_frame.f_locals.items ():
            if not isinstance (v, _WASType):
                continue
            self.coro.gi_frame.f_locals [n] = self._was
        ctypes.pythonapi.PyFrame_LocalsToFast(ctypes.py_object (self.coro.gi_frame), ctypes.c_int (0))

    def _determine_response_type (self):
        self._rtype = utils.determine_response_type (self._was.request)
        if self._rtype == 'websocket':
            self.resp_status = "101 Web Socket Protocol Handshake"

    def collect_data (self):
        while 1:
            try:
                task = next (self.coro)
            except StopIteration as e:
                value = utils.serialize (self._rtype, e.value)
                if value and isinstance (value, (str, bytes)):
                    self.contents.append (value.encode () if isinstance (value, str) else value)
                    return
                return value

            if isinstance (task, Task):
                return task

            task = utils.serialize (self._rtype, task)
            if task is not None:
                self.contents.append (task.encode () if isinstance (task, str) else task)

    def deallocate (self):
        # clean home
        if self._was is None:
            return
        self._was = None
        self.input_streams = []
        self._waiting_input = False

    def streaming_postprocessing (self, exc_info):
        self._was.request.postprocessing (self._was, self.producer, exc_info)
        self.deallocate ()

    def close (self, content = None, exc_info = None):
        content = utils.serialize (self._rtype, content)
        if self.producer:
            if isinstance (content, (str, bytes)):
                self.producer.send (content)
                content = None
            self.producer.execute_when_done (
                lambda x = exc_info: self.streaming_postprocessing (x)
            )
            self.producer.close ()
            return

        if isinstance (content, API) and self._was.env.get ('ATILA_SET_SEPC'):
            content.set_spec (self._was.app)

        return content

    def on_completed (self, was, task):
        response = was.response
        while 1:
            content = None
            expt = None
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

                if not isinstance (next_task, Task):
                    if next_task is not None:
                        next_task = utils.serialize (self._rtype, next_task)
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

                    elif self.contents:
                        self.producer.send (b''.join (self.contents))
                        self.contents = []

            except MemoryError:
                raise

            except HTTPError as e:
                response.start_response (e.status)
                content = content or response.build_error_template (e.explain or (was.app.debug and e.exc_info), e.errno, was = was)
                return self.close (content, sys.exc_info ())

            except:
                was.traceback ()
                response.start_response ("502 Bad Gateway")
                content = content or response.build_error_template (was.app.debug and sys.exc_info () or None, 0, was = was)
                return self.close (content, sys.exc_info ())

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
        task = self.collect_data ()
        if task is None:
            return self.close (b''.join (self.contents))
        if not isinstance (task, Task):
            return self.close (task)

        if hasattr (task, 'set_proxy_coroutine'):
            proxy = self.collect_incomming_stream ()
            next (proxy)
            task.set_proxy_coroutine (proxy)
            self._waiting_input = True # must next task.set_proxy_coroutine
            self.producer = producers.sendable_producer (b'')
            self._was.response.current_producer = self.producer
            self._was.response.set_status (self.resp_status)
            return self.producer
        return task if hasattr (task, "_single") else task.then (self.on_completed, self._was)
