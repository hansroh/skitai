
class HTTPError (Exception):
    def __init__ (self, status = "200 OK"):
        self.status = status
        