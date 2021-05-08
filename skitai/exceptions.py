import sys

class HTTPError (Exception):
    def __init__ (self, status = "200 OK", explain = "", errno = 0, traceback = False):
        self.status = status
        self.explain = explain
        self.errno = errno
        self.exc_info = traceback and sys.exc_info () or None


class TaskError (Exception):
    pass

