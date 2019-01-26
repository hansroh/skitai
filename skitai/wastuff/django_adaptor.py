#------------------------------------------------------------
# Cookie and Session Adaptor Between Skitai and Django 
# 
# Available:
#
#   request.user
#   request.session
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
    from django.contrib.auth.middleware import AuthenticationMiddleware

except:
    class WSGIRequest:
        def __init__ (self, env):
            raise SystemError ("Django does not be installed or misconfigured")
    
else:
   DjangoSession = SessionMiddleware ()
   DjangoAuthentication = AuthenticationMiddleware ()


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
    def __init__ (self, was):
        self.was = was
        WSGIRequest.__init__ (self, was.env)
        
        # making self.session
        DjangoSession.process_request (self)
        # making self.user
        DjangoAuthentication.process_request (self)        
        
    def authenticate (self, username, password):
        return auth.authenticate (self, username = username, password = password)
    
    def login (self, user):
        auth.login (self, user)
        
    def logout (self):
        auth.logout (self)
        
    def update_session_auth_hash (self, user):
        auth.update_session_auth_hash (self, user)
                
    def commit (self):
        response = Response (self.was)
        DjangoSession.process_response (self, response)


def request (was):
    if not WSGIRequest:
        raise SystemError ("Django not installed")
    request = DjangoRequest (was)    
    return request
