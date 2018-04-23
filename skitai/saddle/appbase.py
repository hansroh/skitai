import re, sys
from functools import wraps
from urllib.parse import unquote_plus, quote_plus, urljoin
import os
from aquests.lib import importer, versioning
from types import FunctionType as function
import inspect
from importlib import reload
from skitai import was as the_was
import time, threading
from .storage import Storage
from aquests.lib import evbus
from event_bus.exceptions import EventDoesntExist
import time
import skitai    
            
RX_RULE = re.compile ("(/<(.+?)>)")
    
class AppBase:	
    use_reloader = False
    debug = False
    contrib_devel = False # make reloadable
    # Session
    securekey = None
    session_timeout = None

    #WWW-Authenticate    
    access_control_allow_origin = None
    access_control_max_age = 0    
    authenticate = False
    authorization = "digest"    
    realm = None
    users = {}    
    opaque = None
    
    def __init__ (self, *args, **kargs):            
        self.module = None
        self.packagename = None
        self.wasc = None                
        self._started = False
        self._reloading = False
        self.logger = None
        self.mount_p = "/"
        self.path_suffix_len = 0
        self.route_map = {}
        self.route_priority = []
        self.storage = Storage ()
        
        self.decorating_params = {}
        self.reloadables = {}
        self.last_reloaded = time.time ()
        
        self.bus = evbus.EventBus ()
        self.events = {}        
        self.lock = threading.RLock ()
        self.init_time = time.time ()        
        self._decos = {}
        self._salt = None
        self._permission_map = {}
        self._jinja2_filters = {}
        self._template_globals = {}
        self._function_specs = {}
        self._function_names = {}
        self._conditions = {}
        self._need_authenticate = {True: [], False: []}        
        self._cond_check_lock = threading.RLock ()
        
        self._binds_server = [None] * 6
        self._binds_request = [None] * 4        
        self.handlers = {}
    
    def get_resource (self, *args):
        return self.joinpath ("resources", *args)
    
    def joinpath (self, *args):    
        return os.path.join (self.home, *args)
                    
    def set_mount_point (self, mount):    
        if not mount:
            self.mount_p = "/"
        elif mount [-1] != "/":
            self.mount_p = mount + "/"
        else:
            self.mount_p = mount
        self.path_suffix_len = len (self.mount_p) - 1
                
    def init (self, module, packagename = "app", mount = "/"):
        self.module = module    
        self.packagename = packagename
        self.set_mount_point (mount)
        
        if self.module:
            self.abspath = self.module.__file__
            if self.abspath [-3:] != ".py":
                self.abspath = self.abspath [:-1]
            self.update_file_info    ()
        
    def __getitem__ (self, k):
        return self.route_map [k]
    
    def get_file_info (self, module):        
        stat = os.stat (module.__file__)
        return stat.st_mtime, stat.st_size
       
    def update_file_info (self):
        stat = os.stat (self.abspath)
        self.file_info = (stat.st_mtime, stat.st_size)
        
    #------------------------------------------------------    
    @property
    def salt (self):
        if self._salt:
            return self._salt
        self._salt = self.securekey.encode ("utf8")
        return self._salt 
    
    def set_default_session_timeout (self, timeout):
        self.session_timeout = timeout
                 
    def set_devel (self, debug = True, use_reloader = True):
        self.debug = debug
        self.use_reloader = use_reloader
    
    # decorative management ----------------------------------------------
    
    PACKAGE_DIRS = ["decorative", "package", "appack"]
    CONTRIB_DIR = os.path.join (os.path.dirname (skitai.__spec__.origin), 'saddle', 'contrib', 'decorative')
            
    def add_package (self, *names):
        for name in names:
            self.PACKAGE_DIRS.append (name)
    
    def find_watchables (self, module):
        for attr in dir (module):
            v = getattr (module, attr)
            try:
                modpath = v.__spec__.origin
            except AttributeError:
                continue            
            if not modpath:
                continue            
            if v in self.reloadables:
                continue
            if self.contrib_devel:
                if modpath.startswith (self.CONTRIB_DIR):
                    self.watch (v)
                    continue
            for package_dir in self._package_dirs:
                if modpath.startswith (package_dir):                    
                    self.watch (v)                    
                    break
        
    def decorate_with (self, module, *args, **karg):
        self.decorating_params [module.__name__] = (args, karg)
        
    def watch (self, module):
        if hasattr (module, "decorate"):
            params = self.decorating_params.get (module.__name__)
            if params:            
                args, karg = params
                module.decorate (self, *args, **karg)
            else:
                module.decorate (self)
                
        try:
            self.reloadables [module] = self.get_file_info (module)
        except FileNotFoundError:
            return
        
        # find recursively
        self.find_watchables (module)
                
    def maybe_reload (self):
        if time.time () - self.last_reloaded < 1.0:
            return
        
        self._reloading = True    
        for module in list (self.reloadables.keys ()):
            try:
                fi = self.get_file_info (module)
            except FileNotFoundError:
                del self.reloadables [module]
                continue
                
            if self.reloadables [module] != fi:
                self.log ("reloading decorative, %s" % module.__file__, "info")                
                newmodule = reload (module)                
                del self.reloadables [module]
                self.watch (newmodule)                
        
        self.last_reloaded = time.time ()
        self._reloading = False
        
    # function param saver ------------------------------------------
    def save_function_spec_for_routing (self, func):
        # save original function spec for preventing distortion by decorating wrapper
        # all wrapper has *args and **karg but we want to keep original function spec for auto parametering call
        if func.__name__ not in self._function_specs:
            # save origin spec
            self._function_specs [func.__name__] = inspect.getargspec(func)
    
    def get_function_spec_for_routing (self, func):
            return self._function_specs.get (func.__name__)
    
    # logger ----------------------------------------------------------
    def set_logger (self, logger):
        self.logger = logger 
        
    def log (self, msg, type = "info"):
        self.logger (msg, type)
    
    def trace (self):
        self.logger.trace ()
                    
    # app life cycling -------------------------------------------    
    def before_mount (self, f):
        self._binds_server [0] = f        
        return f
    start_up = before_mount
    startup = before_mount
     
    def mounted (self, f):
        self._binds_server [3] = f
        return f
    
    def before_reload (self, f):
        self._binds_server [5] = f
        return f    
    onreload = before_reload
    reload = before_reload
    
    def reloaded (self, f):
        self._binds_server [1] = f
        return f
    
    def before_umount (self, f):
        self._binds_server [4] = f
        return f
    umount = before_umount
    
    def umounted (self, f):
        self._binds_server [2] = f
        return f
    shutdown = umounted
    
    PHASES = {
        'before_mount': 0,
        'mounted': 3,
        'before_reload': 5,
        'reloaded': 1,
        'before_umount': 4,
        'umounted': 2,        
    }
    def life_cycle (self, phase, obj):
        index = self.PHASES.get (phase)
        func = self._binds_server [index]
        if not func:
            return    
        try:
            func (obj)
        except:
            if self.logger:
                self.logger.trace ()
            else:
                raise                             

    # Request chains ----------------------------------------------                
    def before_request (self, f):
        self._binds_request [0] = f
        return f
    
    def finish_request (self, f):
        self._binds_request [1] = f
        return f
    
    def failed_request (self, f):
        self._binds_request [2] = f
        return f
    
    def teardown_request (self, f):
        self._binds_request [3] = f
        return f
        
    # Auth ------------------------------------------------------    
    def auth_required (self, f):    
        self._need_authenticate [True].append (f.__name__)
        return f
    
    def auth_not_required (self, f):
        self._need_authenticate [False].append (f.__name__)
        return f
        
    def login_handler (self, f):
        self._decos ["login_handler"] = f
        return f
    
    def login_required (self, f):
        self.save_function_spec_for_routing (f)
        @wraps(f)
        def wrapper (was, *args, **kwargs):
            _funcs = self._decos.get ("login_handler")
            if _funcs:                
                response = _funcs (was)
                if response is not None:
                    return response
            return f (was, *args, **kwargs)
        return wrapper
    
    def staff_member_check_handler (self, f):
        self._decos ["staff_member_check_handler"] = f
        return f
    
    def staff_member_required (self, f):
        self.save_function_spec_for_routing (f)
        @wraps(f)
        def wrapper (was, *args, **kwargs):
            _funcs = self._decos.get ("staff_member_check_handler")
            if _funcs:
                response = _funcs (was)                    
                if response is not None:
                    return response
            return f (was, *args, **kwargs)
        return wrapper
    
    def permission_check_handler (self, f):
        self._decos ["permission_check_handler"] = f
        return f
    
    def permission_required (self, p):
        def decorator(f):
            self.save_function_spec_for_routing (f)
            self._permission_map [f] = isinstance (p, str) and [p] or p
            @wraps(f)
            def wrapper (was, *args, **kwargs):
                _funcs = self._decos.get ("permission_check_handler")
                if _funcs:
                    response = _funcs (was, self._permission_map [f])                    
                    if response is not None:
                        return response
                return f (was, *args, **kwargs)
            return wrapper
        return decorator
    
    def testpass_required (self, testfunc):
        def decorator(f):
            self.save_function_spec_for_routing (f)            
            @wraps(f)
            def wrapper (was, *args, **kwargs):
                response = testfunc (was)
                if response is False:
                    return was.response ("403 Permission Denied")
                elif response is not True and response is not None:
                    return response
                return f (was, *args, **kwargs)
            return wrapper
        return decorator
    
    # Automation ------------------------------------------------------    
    def preworks (self, *funcs):
        def decorator(f):
            self.save_function_spec_for_routing (f)
            @wraps(f)
            def wrapper (was, *args, **kwargs):
                for func in funcs:
                    response = func (was)
                    if response is not None:
                        return response
                return f (was, *args, **kwargs)
            return wrapper
        return decorator
    
    def postworks (self, *funcs):
        def decorator(f):
            self.save_function_spec_for_routing (f)            
            @wraps(f)
            def wrapper (was, *args, **kwargs):
                for func in funcs:
                    func (was)                    
                return f (was, *args, **kwargs)
            return wrapper
        return decorator
    
    # Conditional Automation ------------------------------------------------------    
    def _check_condition (self, was, key, func, interval, mtime_func):
        now = time.time ()
        with self._cond_check_lock:
            oldmtime, last_check = self._conditions [key]
        
        if not interval or now - last_check > interval:
            mtime = mtime_func (key)                    
            if mtime > oldmtime:
                response = func (was, key)
                with self._cond_check_lock:
                    self._conditions [key] = [mtime, now]
                if response is not None:
                    return response
                    
            elif interval:
                with self._cond_check_lock:
                    self._conditions [key][1] = now                        
        
    def if_updated (self, key, func, interval = 1):
        def decorator(f):
            self.save_function_spec_for_routing (f)
            self._conditions [key] = [0, 0]
            @wraps(f)
            def wrapper (was, *args, **kwargs):
                response = self._check_condition (was, key, func, interval, was.getlu)
                if response is not None:
                    return response
                return f (was, *args, **kwargs)
            return wrapper
        return decorator
        
    def if_file_modified (self, path, func, interval = 1):
        def decorator(f):
            self.save_function_spec_for_routing (f)
            self._conditions [path] = [0, 0]
            @wraps(f)
            def wrapper (was, *args, **kwargs):
                def _getmtime (path): 
                    return os.path.getmtime (path)
                response = self._check_condition (was, path, func, interval, _getmtime)
                if response is not None:
                    return response
                return f (was, *args, **kwargs)
            return wrapper
        return decorator
    
    # Websocket ------------------------------------------------------
    def websocket_config (self, spec, timeout = 60, onopen = None, onclose = None, encoding = "text"):
        def decorator(f):
            self.save_function_spec_for_routing (f)
            @wraps(f)
            def wrapper (was, *args, **kwargs):
                if not was.wshasevent ():
                    return f (was, *args, **kwargs)
                if was.wsinit ():
                    return was.wsconfig (spec, timeout, encoding)
                elif onopen and was.wsopened ():
                    return onopen (was)
                elif onclose and was.wsclosed ():
                    return onclose (was)
                
            return wrapper
        return decorator
    
    # Templaing -------------------------------------------------------    
    def template_global (self, name):    
        def decorator(f):
            self.save_function_spec_for_routing (f)
            @wraps(f)
            def wrapper (*args, **kwargs):                
                return f (the_was._get (), *args, **kwargs)
            self._template_globals [name] = wrapper
            return wrapper
        return decorator
    
    def template_filter (self, name):    
        def decorator(f):
            self._jinja2_filters [name] = f
            @wraps(f)
            def wrapper (*args, **kwargs):                
                return f (*args, **kwargs)            
            return wrapper
        return decorator
        
    # Error handling ------------------------------------------------------        
    def get_error_page (self, error):
        handler = self.handlers.get (error ['code'], self.handlers.get (0))
        if not handler:
            return
        was = the_was._get ()    
        # reset was.app for rendering
        was.app = self
        content =    handler [0] (was, error)
        was.app = None
        return content
        
    def add_error_handler (self, errcode, f, **k):
        self.handlers [errcode] = (f, k)        
        
    def error_handler (self, errcode, **k):
        def decorator(f):
            self.add_error_handler (errcode, f, **k)
            @wraps(f)
            def wrapper (*args, **kwargs):
                return f (*args, **kwargs)
            return wrapper
        return decorator
    
    def default_error_handler (self, f):
        self.add_error_handler (0, f)
        return f
    
    defaulterrorhandler = default_error_handler
    errorhandler = error_handler
    
    # URL Building ------------------------------------------------
    def url_for (self, thing, *args, **kargs):
        if thing.startswith ("/"):
            return self.basepath [:-1] + self.mount_p [:-1] + thing
        
        script_name_only = "__resource_path_only__" in kargs                    
        for func, name, fuvars, favars, numvars, str_rule, options in self.route_map.values ():
            if thing != name: continue
            if script_name_only:
                url = str_rule
                if favars:
                    s = url.find ("<")
                    if s != -1:
                        url = url [:s]
                return self.url_for (url)
            
            params = {}
            try:
                currents = kargs.pop ("__defaults__")
            except KeyError:
                currents = {}
            else:
                for k, v in currents.items ():
                    if k in fuvars:
                        params [k] = v                        
            
            assert len (args) <= len (fuvars), "Too many params, this has only %d params(s)" % len (fuvars)                    
            for i in range (len (args)):
                params [fuvars [i]] = args [i]
            
            for k, v in kargs.items ():
                params [k] = v
            
            url = str_rule
            if favars: #fancy [(name, type),...]. /fancy/<int:cid>/<cname>
                for n, t in favars:
                    if n not in params:
                        try:
                            params [n] = currents [n]
                        except KeyError:
                            try:
                                params [n] = options ["defaults"][n]
                            except KeyError:
                                raise AssertionError ("Argument '%s' missing" % n)
                        
                    value = quote_plus (str (params [n]))
                    if t == "string":
                        value = value.replace ("+", "_")
                    elif t == "path":
                        value = value.replace ("%2F", "/")
                    url = url.replace ("<%s%s>" % (t != "string" and t + ":" or "", n), value)
                    del params [n]
            
            if params:
                url = url + "?" + "&".join (["%s=%s" % (k, quote_plus (str(v))) for k, v in params.items ()])
                
            return self.url_for (url)
        raise NameError ("{} not found".format (str (thing)))
    
    build_url = url_for
        
    # Routing ------------------------------------------------------                            
    def route (self, rule, **k):
        def decorator (f):
            self.add_route (rule, f, **k)
            @wraps(f)
            def wrapper (*args, **kwargs):
                return f (*args, **kwargs)
            return wrapper
        return decorator
            
    def get_route_map (self):
        return self.route_map
    
    def set_route_map (self, route_map):
        self.route_map = route_map
                                    
    def try_rule (self, path_info, rule, rulepack):
        f, n, l, a, c, s, options = rulepack
        
        arglist = rule.findall (path_info)
        if not arglist: 
            return None, None
        
        arglist = arglist [0]
        if type (arglist) is not tuple:
            arglist = (arglist,)
            
        kargs = {}
        for i in range(len(arglist)):
            an, at = a [i]
            if at == "int":
                kargs [an] = int (arglist [i])
            elif at == "float":
                kargs [an] = float (arglist [i])
            elif at == "path":
                kargs [an] = unquote_plus (arglist [i])
            else:        
                kargs [an] = unquote_plus (arglist [i]).replace ("_", " ")
        return f, kargs
    
    def add_route (self, rule, func, **options):
        if not rule or rule [0] != "/":
            raise AssertionError ("Url rule should be starts with '/'")
        
        if not self._started and not self._reloading and func.__name__ in self._function_names:
            raise NameError ("Function <{}> is already defined".format (func.__name__))
        self._function_names [func.__name__] = None        
            
        fspec = self._function_specs.get (func.__name__) or inspect.getargspec(func)
        options ["args"] = fspec.args [1:]
        options ["varargs"] = fspec.varargs
        options ["keywords"] = fspec.keywords
        
        if fspec.defaults:
            defaults = {}
            argnames = fspec.args[(len (fspec.args) - len (fspec.defaults)):]
            for i in range (len (fspec.defaults)):
                defaults [argnames [i]] = fspec.defaults[i]
            options ["defaults"] = defaults
        
        s = rule.find ("/<")
        if s == -1:    
            self.route_map [rule] = (func, func.__name__, func.__code__.co_varnames [1:func.__code__.co_argcount], None, func.__code__.co_argcount - 1, rule, options)                        
        else:
            s_rule = rule
            rulenames = []
            urlargs = RX_RULE.findall (rule)
            options ["urlargs"] = len (urlargs)
            for r, n in urlargs:
                if n.startswith ("int:"):
                    rulenames.append ((n[4:], n[:3]))
                    rule = rule.replace (r, "/([0-9]+)")
                elif n.startswith ("float:"):
                    rulenames.append ((n[6:], n [:5]))
                    rule = rule.replace (r, "/([.0-9]+)")
                elif n.startswith ("path:"):
                    rulenames.append ((n[5:], n [:4]))
                    rule = rule.replace (r, "/(.+)")    
                else:
                    rulenames.append ((n, "string"))
                    rule = rule.replace (r, "/([^/]+)")
            rule = "^" + rule + "$"            
            re_rule = re.compile (rule)                
            self.route_map [re_rule] = (func, func.__name__, func.__code__.co_varnames [1:func.__code__.co_argcount], tuple (rulenames), func.__code__.co_argcount - 1, s_rule, options)
            self.route_priority.append ((s, re_rule))
            self.route_priority.sort (key = lambda x: x [0], reverse = True)            
        
    def get_routed (self, method_pack):
        if not method_pack: 
            return
        temp = method_pack
        while 1:
            routed = temp [1]
            if type (routed) is not list:
                return routed
            temp = routed
                    
    def route_search (self, path_info):
        if not path_info:
            return self.url_for ("/"), self.route_map ["/"]
        if path_info in self.route_map:
            return self.route_map [path_info][0], self.route_map [path_info]
        trydir = path_info + "/"
        if trydir in self.route_map:
            return self.url_for (trydir), self.route_map [trydir]
        raise KeyError
                    
    def get_package_method (self, path_info, command, content_type, authorization, use_reloader = False):        
        if not (path_info.startswith (self.mount_p) or (path_info + "/").startswith (self.mount_p)):
            return None, None, None, None, None, 0
        
        path_info = path_info [self.path_suffix_len:]
        app, method, kargs, matchtype = self, None, {}, 0                
        
        # 1st, try find in self
        try:
            method, current_rule = self.route_search (path_info)
            
        except KeyError:
            for priority, rule in self.route_priority:
                current_rule = self.route_map [rule]
                method, kargs = self.try_rule (path_info, rule, current_rule)
                if method: 
                    match = (rule, current_rule)
                    matchtype = 2
                    options = current_rule [-1]
                    break
        
        else:            
            match = path_info
            if type (method) is not function:
                # object move
                matchtype = -1
            else:    
                matchtype = 1
                options = current_rule [-1]                
                
        if method is None:
            return None, None, None, None, None, 0
        
        if matchtype == -1: # 301 move
            return app, method, None, None, None, -1
                
        return app, [self._binds_request [0], method] + self._binds_request [1:4], kargs, options, match, matchtype
    
    # model signal ---------------------------------------------
    def _model_changed (self, sender, **karg):
        model_name = str (sender)[8:-2]
        karg ['x_model_class'] = model_name
        if 'created' not in karg:
            karg ["x_operation"] = 'D'
        elif karg["created"]:
            karg ["x_operation"] = 'C'
        else:
            karg ["x_operation"] = 'U'
        karg ["x_ignore"]    = True
        the_was._get ().setlu (model_name, sender, **karg)
    
    def redirect_signal (self, framework = "django"):
        if framework == "django":    
            from django.db.models.signals import post_save, post_delete        
            post_save.connect (self._model_changed)
            post_delete.connect (self._model_changed)
    model_signal = redirect_signal
            
    # app startup and shutdown --------------------------------------------    
    def cleanup (self):
        # initing app & packages        
        pass
            
    def _start (self, wasc, route, reload = False):
        self.wasc = wasc
        if not route:
            self.basepath = "/"
        elif not route.endswith ("/"):            
            self.basepath = route + "/"
        else:
            self.basepath = route            
        
    def start (self, wasc, route):
        self.bus.emit ("app:starting", wasc)
        self._start (wasc, route)
        self.bus.emit ("app:started", wasc)
        self._started = True
        
    def restart (self, wasc, route):        
        self._reloading = True
        self.bus.emit ("app:restarting", wasc)    
        self._start (wasc, route, True)
        self.bus.emit ("app:restarted", wasc)    
        self._reloading = False
    
    #----------------------------------------------
    
    def on (self, *events):
        def decorator(f):            
            self.save_function_spec_for_routing (f)
            for e in events:
                if self._reloading:
                    try: self.bus.remove_event (f.__name__, e)
                    except EventDoesntExist: pass                
                self.bus.add_event (f, e)
                
            @wraps(f)
            def wrapper(*args, **kwargs):
                return f (*args, **kwargs)
            return wrapper
        return decorator
        
    def emit_after (self, event):
        def outer (f):
            self.save_function_spec_for_routing (f)
            @wraps (f)
            def wrapper(*args, **kwargs):
                returned = f (*args, **kwargs)
                self.emit (event)
                return returned
            return wrapper
        return outer
            
    def emit (self, event, *args, **kargs):
        self.bus.emit (event, the_was._get (), *args, **kargs)
    
    #-----------------------------------------------
    
    def on_broadcast (self, *events):
        def decorator(f):
            self.save_function_spec_for_routing (f)
            for e in events:                
                self.add_event (e, f)
            @wraps(f)
            def wrapper(*args, **kwargs):
                return f (*args, **kwargs)
            return wrapper
        return decorator
    # this is for model signal
    on_signal = on_broadcast
         
    def broadcast_after (self, event):
        def decorator (f):
            self.save_function_spec_for_routing (f)
            @wraps (f)
            def wrapper(*args, **kwargs):
                returned = f (*args, **kwargs)
                the_was._get ().apps.emit (event)
                return returned
            return wrapper
        return decorator
        
    def add_event (self, event, f):
        try:
            del self.events [(f.__name__, event)]
        except KeyError:
            pass
        self.events [(f.__name__, event)] = f
    
    def commit_events_to (self, broad_bus):
        for (fname, event), f in self.events.items ():
            broad_bus.add_event (f, event)
            
    def remove_events (self, broad_bus):
        for (fname, event), f in self.events.items ():
            try:    
                broad_bus.remove_event (fname, event)
            except EventDoesntExist: 
                pass
                   
    # Deprecated -----------------------------------------------    
    @versioning.deprecated
    def reload_package (self):
        importer.reloader (self.module)
        self.update_file_info ()
    
    @versioning.deprecated
    def reloadable (self):
        if self.module is None: return False
        stat = os.stat (self.abspath)
        return self.file_info != (stat.st_mtime, stat.st_size)
       
       