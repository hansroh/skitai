
class HTTPError (Exception):
    def __init__ (self, status = "200 OK", explain = "", errno = 0):
        self.status = status
        self.explain = explain
        self.errno = errno
