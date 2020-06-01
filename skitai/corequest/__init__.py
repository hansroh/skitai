from ..exceptions import HTTPError
from ..utility import make_pushables
import sys

WAS_FACTORY = None

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

        will_be_push = make_pushables (response, content)
        if will_be_push is None:
            return # future

        try:
            for part in will_be_push:
                response.push (part)
            response.done ()

        finally:
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
