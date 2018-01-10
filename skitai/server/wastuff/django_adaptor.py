#------------------------------------------------------------
# Cookie and Session Adaptor Between Skitai and Django 
# 
# Available:
#
#   request.user
#   request.session
#   request.COOKIE
#
# Jan 10, 2018
# Hans Roh
#------------------------------------------------------------

try:
    from django.contrib import auth
    from django.core.handlers.wsgi import WSGIRequest
    from django.utils.functional import SimpleLazyObject
    from django.contrib.auth.middleware import get_user
    from django.contrib.sessions.middleware import SessionMiddleware
except ImportError:
    WSGIRequest = None
else:
   DjangoSession = SessionMiddleware ()
   
class Response:
    def __init__ (self, was):
        self.was = was
    
    @property
    def status_code (self):
        return int (self.was.response.get_status () [:3])
                    
    def set_cookie (self, k, v, max_age, expires, domain, path, secure, httponly):
        self.was.cookie.set (k, v, expires, path, domain, secure, httponly)        
    
    def delete_cookie (self, key, path, domain):
        self.was.cookie.remove (key, path, domain)
    
    def has_header (self, k):
        return self.was.response.get_header (k)
    
    def __getitme__ (self, k):
        return self.was.response [k]
        
    def __setitem__ (self, k, v):
        self.was.response [k] = v


class DjangoRequest (WSGIRequest):
    def authenticate (self, username, password):
        return auth.authenticate (self, username = username, password = password)
    
    def login (self, user):
        auth.login (self, user)
        self._commit ()
        
    def logout (self):
        auth.logout (self)
        self._commit ()
    
    def update_session_auth_hash (self, user):
        auth.update_session_auth_hash (self, user)
        
    def _commit (self):    
        response = Response (self.skito_was)
        DjangoSession.process_response (self, response)
        
        # delete back refs        
        response.was = None
        request.skito_was = None
        self.skito_was.request.django = None


def request (was):
    if not WSGIRequest:
        raise SystemError ("Django not installed")
    request = DjangoRequest (was.env)
    DjangoSession.process_request (request)    
    request.user = SimpleLazyObject (lambda: get_user (request))
    request.skito_was = was
    return request
