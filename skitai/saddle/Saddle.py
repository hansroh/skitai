import time
import os, sys
from . import appbase, multipart_collector, cookie, session, grpc_collector, ws_executor
from . import wsgi_executor, xmlrpc_executor, grpc_executor, jsonrpc_executor
from aquests.protocols.grpc import discover
from aquests.protocols.http import http_util
from skitai import was as the_was
from hashlib import md5
import base64
from .config import Config
from sqlphile import Template
import skitai    
from aquests.dbapi import DB_PGSQL, DB_POSTGRESQL, DB_SQLITE3, DB_REDIS, DB_MONGODB
from jinja2 import Environment, FileSystemLoader, ChoiceLoader

class AuthorizedUser:
    def __init__ (self, user, realm, info = None):
        self.name = user
        self.realm = realm
        self.info = info
    
    def __str__ (self):
        return self.name
        
        
class Saddle (appbase.AppBase):
    templates_dirs = []
    PRESERVES_ON_RELOAD = ["reloadables"]
    
    def __init__ (self, app_name):
        appbase.AppBase.__init__ (self)
        self.app_name = app_name
        self.home = None
        self.jinja_env = None        
        self.chameleon = None
        self.sqlphile = None
        # for bus, set by wsgi_executor
        self.cached_paths = {}        
        self.cached_rules = []
        self.config = Config (preset = True)
        self._package_dirs = []
        self._aliases = []
        
    #--------------------------------------------------------
    
    def alias (self, *args, **karg):
        name, args = skitai.alias (*args, **karg)                
        skitai.dconf ["clusters"].pop (name)
        ctype, members, policy, ssl = args
        self._aliases.append ((ctype, "{}:{}".format (name, self.app_name), members, ssl, policy))
        
    def make_client (self, point = "/", approot = ".", numthreads = 1):
        from ..server import offline
        from ..server.offline import client    
        
        class Client (client.Client):        
            def make_request (self, *args, **karg):
                request = client.Client.make_request (self, *args, **karg)
                return self.handle_request (request)    
            
            def handle_rpc (self, request):
                return self.handle_request (request)
                
            def __enter__ (self):
                return self
                
            def __exit__ (self, type, value, tb):
                pass
                     
        offline.activate ()
        offline.install_vhost_handler ()        
        offline.mount (point, (self, approot))
        return Client ()
    
    # template engine -----------------------------------------------        
    def skito_jinja (self, option = 0):
        if option == 0:    
            self.jinja_overlay ("${", "}", "<%", "%>", "<!---", "--->")
        elif option == 1:
            self.jinja_overlay ("${", "}", "{%", "%}", "{#", "#}")
        elif option == 2:
            self.jinja_overlay ("{*", "*}", "{%", "%}", "{#", "#}")    
        elif option == 3:
            self.jinja_overlay ("{#", "#}", "{%", "%}", "<!---", "--->")        
        elif option == 4:
            self.jinja_overlay ("##", "##", "{%", "%}", "<!---", "--->")            
        elif option == 5:
            self.jinja_overlay ("{:", ":}", "{%", "%}", "<!---", "--->")                
        elif option == 6:
            self.jinja_overlay ("<%", "%>", "{%", "%}", "<!---", "--->")                    
        elif option == 7:
            self.jinja_overlay ("{%", "%}", "<%", "%>", "<!---", "--->")
        
    def jinja_overlay (
        self, 
        variable_start_string = "{{",
        variable_end_string = "}}", 
        block_start_string = "{%", 
        block_end_string = "%}", 
        comment_start_string = "{#",
        comment_end_string = "#}",
        line_statement_prefix = "%", 
        line_comment_prefix = "%%",
        **karg
    ):
        from .patches import jinjapatch
        self.jinja_env = jinjapatch.overlay (self.app_name, variable_start_string, variable_end_string, block_start_string, block_end_string, comment_start_string, comment_end_string, line_statement_prefix, line_comment_prefix, **karg)
        
    def render (self, was, template_file, _do_not_use_this_variable_name_ = {}, **karg):
        while template_file and template_file [0] == "/":
            template_file = template_file [1:]    

        if _do_not_use_this_variable_name_: 
            assert not karg, "Can't Use Dictionary and Keyword Args Both"
            karg = _do_not_use_this_variable_name_

        karg ["was"] = was
        karg.update (self._template_globals)
        
        template = self.get_template (template_file)
        self.emit ("template:rendering", template, karg)
        rendered = template.render (**karg)
        self.emit ("template:rendered", rendered)
        return rendered
                    
    def get_template (self, name):
        if name.endswith ('.pt') or name.endswith (".ptal"):
            if self.chameleon is None:
                raise SystemError ('Chameleon template engine is not installed')
            return self.chameleon [name]
        return self.jinja_env.get_template (name)        
    
    def get_template_loader (self):
        templates = [FileSystemLoader (os.path.join (self.home, "templates"))]
        for tdir in self.templates_dirs:
            templates.append (FileSystemLoader (tdir))
        templates.append (FileSystemLoader(os.path.join (os.path.dirname (__file__), 'contrib', 'templates')))                
        return ChoiceLoader (templates)
    
    # directory management ----------------------------------------------------------    
    def set_home (self, path, module = None):
        self.home = path
        
        # configure jinja --------------------------------------------
        loader = self.get_template_loader ()
        if self.jinja_env:
            # activated skito_jinja
            self.jinja_env.loader = loader
        else:
            self.jinja_env = Environment (loader = loader)
        
        for k, v in self._jinja2_filters.items ():
            self.jinja_env.filters [k] = v
        
        # chameleon -------------------------------------
        try: from chameleon import PageTemplateLoader
        except: pass        
        else:        
            self.chameleon = PageTemplateLoader (
                os.path.join(path, "templates"),
                auto_reload = self.use_reloader,
                restricted_namespace = False
            )
        
        # reconfigure authenticate ------------------------------------------
        for params in self.route_map.values ():
            for b in (True, False):
                if params [1] in self._need_authenticate [b]:
                    params [-1]["authenticate"] = b
                    break
            
        # sqlphile --------------------------------------------
        sqlmap_dir = os.path.join(path, self.config.get ("sqlmap_dir", "sqlmaps"))
        if not os.path.isdir (sqlmap_dir):
            sqlmap_dir = None
        self.sqlphile = Template (self.config.get ("sql_engine", skitai.DB_PGSQL [1:]), sqlmap_dir, self.use_reloader)
        
        # vaild packages --------------------------------------------
        package_dirs = []
        for d in self.PACKAGE_DIRS:
            maybe_dir = os.path.join (path, d)
            if os.path.isdir (maybe_dir):
                self._package_dirs.append (maybe_dir)
    
        if module:
            self.find_watchables (module)
        
    # high level API----------------------------------------------    
    def get_www_authenticate (self):
        if self.authorization == "basic":
            return 'Basic realm="%s"' % self.realm
        else:    
            if self.opaque is None:
                self.opaque = md5 (self.realm.encode ("utf8")).hexdigest ()
            return 'Digest realm="%s", qop="auth", nonce="%s", opaque="%s"' % (
                self.realm, http_util.md5uniqid (), self.opaque
            )
            
    def get_password (self, user):
        info = self.users.get (user)
        if not info:
            return None, 0 # passwrod, encrypted
        return type (info) is str and (info, 0) or info [:2]
    
    def get_info (self, user):
        info = self.users.get (user)
        if not info: return None
        return (type (info) is not str and len (info) == 3) and info [-1] or None
                
    def authorize (self, auth, method, uri):
        if self.realm is None or not self.users:
            return
                
        if auth is None:
            return self.get_www_authenticate ()
        
        # check validate: https://evertpot.com/223/
        amethod, authinfo = auth.split (" ", 1)
        if amethod.lower () != self.authorization:
            return self.get_www_authenticate ()
        
        if self.authorization == "basic":
            basic = base64.decodestring (authinfo.encode ("utf8")).decode ("utf8")
            current_user, current_password = basic.split (":", 1)
            password, encrypted = self.get_password (current_user)
            if encrypted:
                raise AssertionError ("Basic authorization can't handle encrypted password")
            if password ==  current_password:
                return AuthorizedUser (current_user, self.realm, self.get_info (current_user))
                
        else:
            method = method.upper ()
            infod = {}
            for info in authinfo.split (","):
                k, v = info.strip ().split ("=", 1)
                if not v: return self.get_www_authenticate ()
                if v[0] == '"': v = v [1:-1]
                infod [k]     = v
            
            current_user = infod.get ("username")
            if not current_user:
                return self.get_www_authenticate ()
            
            password, encrypted = self.get_password (current_user)
            if not password:
                return self.get_www_authenticate ()
                
            try:
                if uri != infod ["uri"]:                    
                    return self.get_www_authenticate ()
                if encrypted:    
                    A1 = password
                else:
                    A1 = md5 (("%s:%s:%s" % (infod ["username"], self.realm, password)).encode ("utf8")).hexdigest ()
                A2 = md5 (("%s:%s" % (method, infod ["uri"])).encode ("utf8")).hexdigest ()
                Hash = md5 (("%s:%s:%s:%s:%s:%s" % (
                    A1, 
                    infod ["nonce"],
                    infod ["nc"],
                    infod ["cnonce"],
                    infod ["qop"],
                    A2
                    )).encode ("utf8")
                ).hexdigest ()

                if Hash == infod ["response"]:
                    return AuthorizedUser (current_user, self.realm, self.get_info (current_user))
                    
            except KeyError:
                pass
        
        return self.get_www_authenticate ()
    
    def is_allowed_origin (self, request, allowed_origins):
        origin = request.get_header ('Origin')
        if not origin:
            return True
        if not allowed_origins:
            allowed_origins = ["%s://%s" % (request.get_scheme (), request.get_header ("host", ""))]
        elif "*" in allowed_origins:
            return True    
        if origin in allowed_origins:
            return True
        return False
        
    def is_authorized (self, request, authenticate):
        if not authenticate:
            return True
        
        www_authenticate = self.authorize (request.get_header ("Authorization"), request.command, request.uri)
        if type (www_authenticate) is str:
            request.response.set_header ('WWW-Authenticate', www_authenticate)
            return False
        elif www_authenticate:
            request.user = www_authenticate                
        return True
    
    def get_collector (self, request):
        ct = request.get_header ("content-type")
        if not ct: return
        if ct.startswith ("multipart/form-data"):
            return multipart_collector.MultipartCollector
            
        if ct.startswith ("application/grpc"):
            try:
                i, o = discover.find_type (request.uri [1:])
            except KeyError:
                raise NotImplementedError            
            return grpc_collector.grpc_collector            
                    
    def get_method (self, path_info, request):        
        command = request.command.upper ()
        content_type = request.get_header_noparam ('content-type')
        authorization = request.get_header ('authorization')        
        current_app, method = self, None
        
        with self.lock:
            if self.use_reloader:
                self.maybe_reload ()
                
            try:
                method, options = self.cached_paths [path_info]
                kargs = {}
            except KeyError:
                ind = 0                
                for rulepack, _method, _options in self.cached_rules:
                    _found, _kargs = self.try_rule (path_info, rulepack [0], rulepack [1])
                    if _found:
                        method = _method
                        kargs = _kargs
                        options = _options
                        break
                    ind += 1
                                    
        if not method:
            if self.use_reloader:
                self.lock.acquire ()
            try:    
                current_app, method, kargs, options, match, matchtype = self.get_package_method (path_info, command, content_type, authorization, self.use_reloader)
            finally:    
                if self.use_reloader: 
                    self.lock.release ()
            
            if matchtype == -1:
                return current_app, method, None, options, 301
            
            if not method:
                return current_app, None, None, options, 404
                
            if not self.use_reloader:
                if matchtype == 1:
                    with self.lock:
                        self.cached_paths [match] = (method, options)
                                
                elif matchtype == 2:
                    with self.lock:
                        self.cached_rules.append ([match, method, options])
                        # sort by length of rule desc
                        self.cached_rules.sort (key = lambda x: len (x [0][-1][-2]), reverse = True)
                
        resp_code = 0
        if options:
            allowed_types = options.get ("content_types", [])
            if allowed_types and content_type not in allowed_types:
                return current_app, None, None, options, 415 # unsupported media type
            
            allowed_methods = options.get ("methods", [])            
            if allowed_methods and command not in allowed_methods:                
                return current_app, None, None, options, 405 # method not allowed
            
            if command == "OPTIONS":                
                request_method = request.get_header ("Access-Control-Request-Method")
                if request_method and request_method not in allowed_methods:
                    return current_app, None, None, options, 405 # method not allowed
            
                response = request.response
                response.set_header ("Access-Control-Allow-Methods", ", ".join (allowed_methods))
                access_control_max_age = options.get ("access_control_max_age", self.access_control_max_age)    
                if access_control_max_age:
                    response.set_header ("Access-Control-Max-Age", str (access_control_max_age))
                
                requeste_headers = request.get_header ("Access-Control-Request-Headers", "")        
                if requeste_headers:
                    response.set_header ("Access-Control-Allow-Headers", requeste_headers)
                    
                resp_code = 200
            
            else:
                if not self.is_allowed_origin (request, options.get ("access_control_allow_origin", self.access_control_allow_origin)):
                    resp_code =  403
                elif not self.is_authorized (request, options.get ("authenticate", self.authenticate)):
                    resp_code =  401
        
        if resp_code in (401, 200):
            authenticate = options.get ("authenticate", self.authenticate)
            if authenticate:
                request.response.set_header ("Access-Control-Allow-Credentials", "true")
                            
        access_control_allow_origin = options.get ("access_control_allow_origin", self.access_control_allow_origin)
        if access_control_allow_origin and access_control_allow_origin != 'same':
            request.response.set_header ("Access-Control-Allow-Origin", ", ".join (access_control_allow_origin))
        
        return current_app, method, kargs, options, resp_code
    
    #------------------------------------------------------
    def create_on_demand (self, was, name):
        class G: 
            pass
        
        # create just in time objects
        if name == "cookie":
            return cookie.Cookie (was.request, self.securekey, self.basepath [:-1], self.session_timeout)
            
        elif name in ("session", "mbox"):
            if not was.in__dict__ ("cookie"):
                was.cookie = cookie.Cookie (was.request, self.securekey, self.basepath [:-1], self.session_timeout)            
            if name == "session":
                return was.cookie.get_session ()
            if name == "mbox":
                return was.cookie.get_notices ()
                
        elif name == "g":
            return G ()
        
    def cleanup_on_demands (self, was):
        if was.in__dict__ ("g"):
            del was.g
        if not was.in__dict__ ("cookie"):
            return
        for j in ("session", "mbox"):
            if was.in__dict__ (j):        
                delattr (was, j)
        del was.cookie
                                        
    def __call__ (self, env, start_response):
        was = env ["skitai.was"]        
        was.app = self        
        was.response = was.request.response
        
        content_type = env.get ("CONTENT_TYPE", "")                
        if content_type.startswith ("text/xml") or content_type.startswith ("application/xml"):
            result = xmlrpc_executor.Executor (env, self.get_method) ()
        elif content_type.startswith ("application/grpc"):
            result = grpc_executor.Executor (env, self.get_method) ()            
        elif content_type.startswith ("application/json-rpc"):
            result = jsonrpc_executor.Executor (env, self.get_method) ()    
        elif env.get ("websocket.params"):
            result = ws_executor.Executor (env, None) ()
        else:    
            result = wsgi_executor.Executor (env, self.get_method) ()
    
        self.cleanup_on_demands (was) # del session, mbox, cookie, g
        del was.response        
        was.app = None        
        return result
        