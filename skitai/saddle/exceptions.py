
class HTTPError (Exception):
    def __init__ (self, status = "200 OK", explain = ""):
        self.status = status
        self.explain = explain
        