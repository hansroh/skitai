from ..exceptions import HTTPError
from ..utility import make_pushables
import sys

WAS_FACTORY = None

class corequest:
    def _get_was (self):
        global WAS_FACTORY
        if WAS_FACTORY is None:
            from skitai import was
            WAS_FACTORY = was

        try:
            _was = WAS_FACTORY._get ()
        except TypeError:
            return
        else:
            assert hasattr (_was, 'app'), 'corequest future is available on only Atila'
        return _was._clone (True)

    def _late_respond (self, tasks):
        # NEED self._fulfilled and self._was
        response = self._was.response
        try:
            content = self._fulfilled (self._was, tasks)
            self._fulfilled = None
            will_be_push = make_pushables (response, content)
            content = None
        except MemoryError:
            raise
        except HTTPError as e:
            response.start_response (e.status)
            content = response.build_error_template (e.explain, e.errno, was = self._was)
        except:
            self._was.traceback ()
            response.start_response ("502 Bad Gateway")
            content = response.build_error_template (self._was.app.debug and sys.exc_info () or None, 0, was = self._was)

        if content:
           will_be_push = make_pushables (response, content)

        if will_be_push is None:
            return

        for part in will_be_push:
            if len (will_be_push) == 1 and type (part) is bytes and len (response) == 0:
                response.update ("Content-Length", len (part))
            response.push (part)
        response.done ()

    # basic methods --------------------------------------
    def get_timeout (self):
        return self._timeout

    def set_timeout (self, timeout):
        self._timeout = timeout

    def returning (self, returning):
        # coreauest.then (callback).returning ("201 Created")
        return returning

    # implementables --------------------------------------
    def then (self, func):
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
