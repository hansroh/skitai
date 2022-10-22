# 2014. 12. 9 by Hans Roh hansroh@gmail.com

__version__ = "0.53.1"

version_info = tuple (map (lambda x: not x.isdigit () and x or int (x),  __version__.split (".")))
assert len ([x for  x in version_info [:2] if isinstance (x, int)]) == 2, 'major and minor version should be integer'

NAME = "Skitai/%s.%s" % version_info [:2]

from rs4.protocols import lifetime as lifetime_aq
from rs4 import deco, importer
from rs4.psutil import service
import threading
import sys, os
from rs4.protocols.sock.impl.smtp import composer
import tempfile
from rs4 import argopt
from .backbone import lifetime
from functools import wraps
from rs4.termcolor import tc
import getopt as libgetopt
from rs4 import pathtool
from .wastuff.preference import Preference
from rs4  import evbus
from .tasks.coroutine import Coroutine


argopt.add_option ('-d', desc = "start as daemon, equivalant with `start` command") # lower version compatible

argopt.add_option (None, '---profile', desc = "log for performance profiling")
argopt.add_option (None, '---memtrack', desc = "show memory status")
argopt.add_option (None, '---gc', desc = "enable manual GC")

argopt.add_option (None, '--deploy=VALUE', desc = "set SKITAIENV env to VALUE like QA, TEST, ...")
argopt.add_option (None, '--devel', desc = "set SKITAIENV environ env to DEVEL")

argopt.add_option (None, '--port=TCP_PORT_NUMBER', desc = "http/https port number")
argopt.add_option (None, '--quic=UDP_PORT_NUMBER', desc = "http3/quic port number")
argopt.add_option (None, '--workers=WORKERS', desc = "number of workers")
argopt.add_option (None, '--threads=THREADS', desc = "number of threads per worker")
argopt.add_option (None, '--tasks=TASKS', desc = "number of concurrent async tasks")

argopt.add_option (None, '--poll=POLLER', desc = "name of poller [select, poll, epoll and kqueue]")
argopt.add_option (None, '--disable-static', desc = "disable static file service")
argopt.add_option (None, '--collect-static', desc = "collect static files")

argopt.add_option (None, '--user=USER', desc = "if run as root, fallback workers owner to user")
argopt.add_option (None, '--group=GROUP', desc = "if run as root, fallback workers owner to group")
argopt.add_option (None, '--smtpda', desc = "start SMTP delivery agent")

dconf = dict (
    mount = {"default": []},
    mount_onfly = {"default": []},
    max_ages = {},
    log_off = [],
    dns_protocol = 'tcp',
    models_keys = set (),
    wasc_options = {},
    backlog = 256,
    max_upload_size = 256 * 1024 * 1024, # 256Mb
    subscriptions = set (),
    background_jobs = [],
    media_url = None,
    media_path = None,
    enable_async = False,
)

def background_task (procname, cmd):
    global dconf
    dconf ['background_jobs'].append ((procname, cmd))

# IMP: DO NOT USE argopt.options ()
if '--deploy' in sys.argv:
    assert '--devel' not in argopt.options (), "--devel is not allowed if --deploy is given"
    os.environ ['SKITAIENV'] = argopt.options ().get ('--deploy')
if "--devel" in sys.argv:
    os.environ ["SKITAIENV"] = "DEVEL"
if os.getenv ("SKITAIENV") is None:
    os.environ ["SKITAIENV"] = "PRODUCTION"

SMTP_STARTED = False
def run_smtpda ():
    global SMTP_STARTED
    if SMTP_STARTED:
        return
    background_task ("smtpda", "{} -m skitai.scripts.skitai smtpda".format (sys.executable))
    SMTP_STARTED = True

if "--smtpda" in sys.argv and os.name != 'nt':
    run_smtpda ()

def set_smtp (server, user = None, password = None, ssl = False, start_service = False):
    composer.set_default_smtp (server, user, password, ssl)
    run_smtpda ()

def test_client (*args, **kargs):
    from .testutil.launcher import Launcher
    return Launcher (*args, **kargs)

environ = {}
def getenv (name, default = None):
    return environ.get (name, default)

def setenv (name, value):
    environ [name] = value

HAS_ATILA = None

DEFAULT_KEEP_ALIVE = 2
DEFAULT_NETWORK_TIMEOUT = 30
DEFAULT_BACKGROUND_TASK_TIMEOUT = 300

STA_REQFAIL = REQFAIL = -1
STA_UNSENT = UNSENT = 0
STA_TIMEOUT = TIMEOUT = 1
STA_NETERR = NETERR = 2
STA_NORMAL = NORMAL = 3

WEBSOCKET_SIMPLE = 1
WEBSOCKET_GROUPCHAT = 5

WS_COROUTINE = 8
WS_REPORTY = WS_CHANNEL = WS_SIMPLE = 1
WS_GROUPCHAT = 5
WS_THREADSAFE_DEPRECATED = 7

# optional executing ways
WS_THREAD = 0
WS_NOPOOL = WS_NOTHREAD = WS_NQ = 128
WS_THREADSAFE = 134
WS_SESSION = 256
WS_CHATTY = WS_CHANNEL | WS_SESSION

WS_EVT_INIT = "init"
WS_EVT_OPEN = "open"
WS_EVT_CLOSE = "close"
WS_EVT_NONE = None

WS_MSG_JSON = "json"
WS_MSG_XMLRPC = "xmlrpc"
WS_MSG_GRPC = "grpc"
WS_MSG_TEXT = "text"
WS_MSG_DEFAULT = "text"

WS_OPCODE_TEXT = 0x1
WS_OPCODE_BINARY = 0x2
WS_OPCODE_CLOSE = 0x8
WS_OPCODE_PING = 0x9
WS_OPCODE_PONG = 0xa

STATUS = 'CONFIGURING'
MEDIA_PATH = None
WASC = None
EVBUS = evbus.EventBus ()

def status ():
    global STATUS
    return STATUS

class _WASPool:
    MAX_CLONES_PER_THREAD = 256

    def __init__ (self):
        self.__wasc = None
        self.__p = {}
        self.__kargs = {}

    def __get_id (self):
        return id (threading.currentThread ())

    def __repr__ (self):
        return "<class skitai.ContextPool at %x, was class: %s>" % (id (self), self.__wasc)

    def __getattr__ (self, attr):
        return getattr (self._get (), attr)

    def __setattr__ (self, attr, value):
        if attr.startswith ("_WASPool__"):
            self.__dict__[attr] = value
        else:
            setattr (self.__wasc, attr, value)
            for _id in self.__p:
                setattr (self.__p [_id], attr, value)

    def __delattr__ (self, attr):
        delattr (self.__wasc, attr)
        for _id in self.__p:
            delattr (self.__p [_id], attr)

    def _start (self, wasc, **kargs):
        self.__wasc = wasc
        self.__kargs = kargs

    def _started (self):
        return self.__wasc

    def _del (self):
        _id = self.__get_id ()
        try: del self.__p [_id]
        except KeyError: pass
        # remove clone
        for i in range (self.MAX_CLONES_PER_THREAD):
            try: del self.__p ['{}x{:02d}'.format (_id, i + 1)]
            except KeyError: break

    def _new (self):
        return self.__wasc (**self.__kargs)

    def _get (self, clone = False):
        if not self._started ():
            global WASC
            return WASC ()

        _id = self.__get_id ()
        for i in range (self.MAX_CLONES_PER_THREAD):
            if clone:
                id = '{}x{:04d}'.format (_id, i + 1)
            else:
                id = _id

            try:
                if id not in self.__p:
                    raise KeyError

                _was = self.__p [id]
                if not clone:
                    return _was

                if _was.env:
                    continue # active
                else:
                    return _was

            except KeyError:
                _was = self.__wasc (**self.__kargs)
                _was.ID = id
                self.__p [id] = _was
                return _was

        raise SystemError ("Too many skitai.was clones")

    def _get_by_id (self, _id):
        return self.__p [_id]

g = None
was = _WASPool ()
def start_was (wasc, **kargs):
    from .wsgiappservice.wasbase import workers_shared_mmap
    global was, g

    g = workers_shared_mmap
    detect_atila ()
    was._start (wasc, **kargs)

def detect_atila ():
    # for avoid recursive importing
    try:
        import atila
    except ImportError:
        pass
    else:
        global HAS_ATILA
        HAS_ATILA = atila.Atila


#-------------------------------------------------
# aliases for WSGI apps
#-------------------------------------------------
def push (*args, **kargs):
    return was.push (*args, **kargs)

def websocket (varname = 60, timeout = 60, onopen = None, onclose = None):
    global was
    if isinstance (varname, int):
        assert not onopen and not onclose, 'skitai.WS_SESSION cannot have onopen or onclose handler'
        timeout, varname = varname, None

    # for non-atila app
    def decorator(f):
        @wraps(f)
        def wrapper (*args, **kwargs):
            was_ = was._get ()
            if not was_.wshasevent ():
                return f (*args, **kwargs)
            if was_.wsinit ():
                return was_.wsconfig (varname and 1 or 1|WS_SESSION, timeout, [varname,], not varname and f (*args, **kwargs) or None)
            elif was_.wsopened ():
                return onopen and onopen () or ''
            elif was_.wsclosed ():
                return onclose and onclose () or ''
        return wrapper
    return decorator

def register_g (*names):
    global dconf
    if isinstance (names [0], (list, tuple)):
        names = list (names [0])
    if was._started ():
        was._luwatcher.add (names)
    else:
        for k in names:
            dconf ["models_keys"].add (k)

    def decorator (cls):
        return cls
    return decorator

def emit (event, *args, **kargs):
    EVBUS.emit (event, *args, **kargs)

def on (self, *events):
    def decorator(f):
        for e in events:
            EVBUS.add_event (f, e)
        @wraps(f)
        def wrapper(*args, **kwargs):
            return f (*args, **kwargs)
        return wrapper
    return decorator

def add_async_task (coro, after_request_callback = None, response_callback = None):
    def _respond_async (was, task):
        try:
            content = task.fetch ()
        finally:
            was.async_executor.done ()
        return content
    return was.async_executor.put ((was._get (), coro, response_callback or _respond_async, after_request_callback))

def add_coroutine_task (coro, after_request_callback = None):
    return Coroutine (was._get (), coro, after_request_callback)

def add_thread_task (target, *args, **kargs):
    _was = was._get ()
    return _was.executors.create_thread (_was.ID, target, *args, **kargs)

def add_process_task (target, *args, **kargs):
    _was = was._get ()
    return _was.executors.create_process (_was.ID, target, *args, **kargs)

def add_subprocess_task (cmd):
    from .tasks.pth import sp_task
    meta = {'__was_id': was._get ().ID}
    return sp_task.Task (cmd, meta)


# GPU allocator -----------------------------------------
def get_gpu_memory ():
    import subprocess as sp
    _output_to_list = lambda x: x.decode ('ascii').split('\n')[:-1]
    COMMAND = "nvidia-smi --query-gpu=memory.used --format=csv"
    memory_free_info = _output_to_list(sp.check_output(COMMAND.split()))[1:]
    memory_free_values = [int(x.split()[0]) for i, x in enumerate(memory_free_info)]
    return memory_free_values

def get_gpu_count ():
    ngpu = len (get_gpu_memory ())
    os.environ ["GPU_COUNT"] = str (ngpu)
    return ngpu

def allocate_gpu ():
    assert os.getenv ("GPU_COUNT"), "call skitai.get_gpu_count () first"
    assert os.getenv ("SKITAI_WORKER_ID"), "skitai worker not started"
    os.environ ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    current_gpu = os.getenv ('SKITAI_WORKER_ID') if int (os.getenv ("GPU_COUNT")) > 1 else "0"
    os.environ ["NVIDIA_VISIBLE_DEVICES"] = os.environ ["CUDA_VISIBLE_DEVICES"] = current_gpu

# Configure --------------------------------------------
def preference (preset = False, path = None, **configs):
    from .wastuff.wsgi_apps import Config
    d = Preference (path and abspath (path) or None)
    d.config = Config (preset)
    for k, v in configs.items ():
        d.config [k] = v
    return d
pref = preference # lower version compatible


PROCESS_NAME = None

def get_proc_title ():
    global PROCESS_NAME

    if PROCESS_NAME is None:
        a, b = os.path.split (os.path.join (os.getcwd (), sys.argv [0]))
        script = b.split(".")[0]

        PROCESS_NAME =  "sktd:%s%s" % (
            os.path.basename (a),
            script != "app" and "-" + script or ''
        )
    return PROCESS_NAME

SWD = None
def getswd ():
    global SWD
    if SWD is None:
        SWD = os.path.dirname (os.path.join (os.getcwd (), sys.argv [0]))
    return SWD

def getenv ():
    return os.environ.get ('SKITAIENV')

def isproduction ():
    return getenv () == "PRODUCTION"

def isdevel ():
    return getenv () == "DEVEL"
is_devel = isdevel

def abspath (*pathes):
    return os.path.normpath (os.path.join (getswd (), *pathes))
joinpath = abspath

Win32Service = None
def set_service (service_class):
    global Win32Service
    Win32Service = service_class

def enable_async (pool = 8):
    global dconf
    assert isinstance (pool, int)
    dconf ['enable_async'] = pool

def use_poll (name):
    from rs4 import asyncore
    polls = dict (
        select = 'poll',
        poll = 'poll2',
        epoll = 'epoll',
        kqueue = 'kqueue',
    )
    lifetime_aq.poll_fun = getattr (asyncore, polls [name])

def set_max_upload_size (size):
    global dconf
    dconf ['max_upload_size'] = size

def set_backlog (backlog):
    global dconf
    dconf ['backlog'] = backlog

def add_wasc_option (k, v):
    global dconf
    dconf ['wasc_options'][k] = v

def manual_gc (interval = 60.0):
    lifetime.manual_gc (interval)

def set_worker_critical_point (cpu_percent = 90.0, continuous = 3, interval = 20):
    from .backbone.http_server import http_server
    from .backbone.https_server import https_server

    http_server.critical_point_cpu_overload = https_server.critical_point_cpu_overload = cpu_percent
    http_server.critical_point_continuous = https_server.critical_point_continuous = continuous
    http_server.maintern_interval = https_server.maintern_interval = interval

def set_max_was_clones_per_thread (val):
    was.MAX_CLONES_PER_THREAD = val

def set_media (url = '/media', path = None):
    global dconf
    assert url, "URL cannot be empty"
    if not url.endswith ('/'):
        url = url + '/'
    assert dconf ['media_path'] is None, "media already specified to {media_url}:{media_path}".format (**dconf)
    if path:
        assert path.startswith ('/'), 'media path should be absolute path'
        path = joinpath (path)
        pathtool.mkdir (path)
        mount (url, path, first = True)
    dconf ['media_url'], dconf ['media_path'] = url, path

def log_off (*path):
    global dconf
    for each in path:
        dconf ['log_off'].append (each)

def set_max_age (path, max_age):
    global dconf
    dconf ["max_ages"][path] = max_age

def set_max_rcache (objmax):
    global dconf
    dconf ["rcache_objmax"] = objmax

def set_keep_alive (timeout):
    global dconf
    dconf ["keep_alive"] = timeout

def config_executors (workers = None, zombie_timeout = DEFAULT_BACKGROUND_TASK_TIMEOUT, process_start_method = None):
    global dconf
    if workers:
        dconf ["executors_workers"] = workers
    if zombie_timeout:
        dconf ["executors_zombie_timeout"] = zombie_timeout
    if process_start_method:
        dconf ["executors_process_start"] = process_start_method

def set_503_estimated_timeout (timeout = DEFAULT_NETWORK_TIMEOUT):
    # 503 error if estimated request processing time is over timeout
    # this don't include network latency
    from .handlers import wsgi_handler
    wsgi_handler.Handler.SERVICE_UNAVAILABLE_TIMEOUT = timeout

def set_request_timeout (timeout):
    global dconf
    dconf ["network_timeout"] = timeout
set_network_timeout = set_request_timeout

def set_was_class (was_class):
    global dconf
    dconf ["wasc"] = was_class

def maybe_django (wsgi_path, appname):
    if not isinstance (wsgi_path, str):
        return
    if appname != "application":
        return
    settings = os.path.join (os.path.dirname (wsgi_path), 'settings.py')
    if os.path.exists (settings):
        root = os.path.dirname (os.path.dirname (wsgi_path))
        sys.path.insert (0, root)
        return root

def mount (point, target, __some = pref (True), *args, **kargs):
    if isinstance (__some, Preference):
        if 'pref' not in kargs:
            kargs ['pref'] = __some
        return _mount (point, target, 'app', *args, **kargs)
    return _mount (point, target, __some, *args, **kargs)

def _mount (point, target, appname = "app", pref = pref (True), host = "default", path = None, name = None, **kargs):
    global dconf

    if isinstance (appname, Preference):
        pref, appname = appname, "app"

    def init_app (modpath, pref):
        srvice_root = os.path.dirname (modpath)
        modinit = os.path.join (srvice_root, "__init__.py")
        if os.path.isfile (modinit):
            mod = importer.from_file ("temp", modinit)
            if hasattr (mod, "bootstrap"): # lower version compat
                mod.__config__ = mod.bootstrap
                del mod.bootstrap
            hasattr (mod, "__config__") and mod.__config__ (pref)

    if hasattr (target, "_ATILA_COMPOSIT"):
        target, extends, overrides = target.unpack ()
        [ pref.extends (e) for e in extends ]
        [ pref.overrides (e) for e in overrides ]

    maybe_django (target, appname)
    if path:
        if isinstance (path, str):
            path = [path]
        path.reverse ()
        for each in path:
            sys.path.insert (0, abspath (each))

    if hasattr (target, "__file__"):
        if name:
            assert name == target.__name__, "invalid mount name, remove name or use '{}'".format (target.__name__)
        else:
            name = target.__name__

        if not hasattr (target, '__app__'):
            if hasattr (target, '__skitai__'):
                target = target.__skitai__
            else:
                raise AttributeError ("__app__ or __skitai__ not defined")

    if 'subscribe' in kargs:
        assert name, 'to subscribe, name must be specified'
        subscribe = kargs ['subscribe']
        if isinstance (subscribe, str):
            subscribe = [subscribe]
        for app in subscribe:
            dconf ['subscriptions'].add ((app, name))

    if hasattr (target, '__app__'):
        pass
    elif type (target) is not str:
        path = os.path.normpath (os.path.join (os.getcwd (), sys.argv [0]))
        if hasattr (target, "ATILA_THE_HUN") and not target.path:
            target.path = path
        target = (target, os.path.dirname (path))
    else:
        if target [0] == "@":
            appname = None
        else:
            tmp = os.path.basename (target).split (":", 1)
            if len (tmp) == 2:
                target, appname = os.path.join (os.path.dirname (target), tmp [0]), tmp [1]
            target = abspath (target)

    if host not in dconf ['mount']:
        dconf ['mount'][host] = []
        dconf ['mount_onfly'][host] = []

    if hasattr (target, '__app__'):
        args = (point,  target, pref, name)
        hasattr (target, "__config__") and target.__config__ (pref)
    elif isinstance (target, tuple):
        args = (point,  target, pref, name)
    elif os.path.isdir (target):
        if '--disable-static' in sys.argv:
            return
        args = (point, joinpath (target), kargs, name)
    elif not appname: # alias
        args = (point, target, kargs, name)
    else:
        target_ = target
        if not target_.endswith ('.py'):
            target_ += '.py'
        if 'PYTEST_CURRENT_TEST' not in os.environ:
            assert os.path.exists (target_),  'app not found: {}'.format (target_)
            with open (target_, encoding = 'utf8') as f:
                if f.read ().find ("atila") != -1:
                    try:
                        import atila # mongkey patch skitai was and Loader
                    except ImportError:
                        pass
        init_app (target, pref)
        args = (point,  (target, appname), pref, name)

    if status () == 'CONFIGURING':
        dconf ['mount'][host].append (args)
    elif args not in dconf ['mount'][host]:
        dconf ['mount_onfly'][host].append (args)

mount_django = mount

def enable_forward (port = 80, forward_port = 443, forward_domain = None, ip = ""):
    global dconf
    dconf ['fws_address'] = ip
    dconf ['fws_port'] = port
    dconf ['fws_to'] = forward_port
    dconf ['fws_domain'] = forward_domain

def enable_file_logging (path = None, kinds = None):
    # loggings : request, server and app
    global dconf
    dconf ['logpath'] = path
    dconf ['file_loggings'] = ['request', 'server', 'app'] if (kinds is None or kinds == 'all') else kinds

def mount_variable (path = None, enable_logging = False):
    global dconf
    if path:
        dconf ['varpath'] = path
    if enable_logging:
        enable_file_logging (os.path.join (path, 'log'), None if enable_logging is True else enable_logging)

def set_access_log_path (path = None):
    enable_file_logging (path, ['request'])

def enable_ssl (certfile, keyfile = None, passphrase = None):
    global dconf
    dconf ["certfile"] = certfile
    dconf ["keyfile"] = keyfile
    dconf ["passphrase"] = passphrase

def get_varpath (name):
    global dconf
    name = name.split (":", 1)[-1].replace ("/", "-").replace (" ", "-")
    default_path = os.name == "posix" and os.path.expanduser ('~/.skitai/%s' % name) or os.path.join (tempfile.gettempdir(), name)
    if 'varpath' in dconf:
        if dconf ['varpath'].find ('/.skitai/') == -1:
            if not os.path.exists (default_path):
                pathtool.mkdir (os.path.expanduser ('~/.skitai'))
                try:
                    os.symlink (dconf ['varpath'], default_path)
                except FileExistsError:
                    pass
        return dconf ['varpath']
    return default_path

def get_logpath (name):
    global dconf
    if dconf.get ('logpath'):
        return dconf ['logpath']
    name = name.split (":", 1)[-1].replace ("/", "-").replace (" ", "-")
    return os.name == "posix" and os.path.expanduser ('~/.skitai/%s/log' % name) or os.path.join (tempfile.gettempdir(), name)

options = None
def add_option (sopt, lopt = None, desc = None, default = None):
    global options
    argopt.add_option (sopt, lopt, desc, default)
    try:
        options = argopt.options ()
    except libgetopt.GetoptError:
        pass

def add_options (*lnames):
    global options
    # deprecated, use add_option for detail description
    for lname in lnames:
        assert lname and lname [0] == "-", "Aurgument should start with '-' or '--'"
        assert lname != "-d" and lname != "-d=", "Aurgument -d is in ussed"
        if lname.startswith ("--"):
            argopt.add_option (None, lname [2:])
        else:
            argopt.add_option (lname [1:])
    options = argopt.options ()

def getopt (sopt = "", lopt = []):
    global options

    # argopt.getopt style
    if "d" in sopt:
        raise SystemError ("-d is used by skitai, please change")
    for each in lopt:
        argopt.add_option (None, each)

    grps = sopt.split (":")
    for idx, grp in enumerate (grps):
        for idx2, each in enumerate (grp):
            if idx2 == len (grp) - 1 and len (grps) > idx + 1:
                argopt.add_option (each + ":")
            else:
                argopt.add_option (each)

    options = argopt.options ()
    opts_ = []
    for k, v in options.items ():
        if k == "-d":
            continue
        elif k.startswith ("---"):
            continue
        opts_.append ((k, v))

    aopt_ = []
    for arg in options.argv:
        if arg in ("start", "stop", "status", "restart"):
            continue
        aopt_.append (arg)
    return opts_, aopt_

def get_options ():
    global options
    options = argopt.options ()
    return options

def get_option (*names):
    global options
    options = argopt.options ()
    for k, v in options.items ():
        if k in names:
            return v

COMMANDS = ["start", "stop", "status", "restart", 'install', 'uninstall', 'remove', 'update']
def get_command ():
    global options, COMMANDS
    options = argopt.options ()
    if '--help' in options:
        print ("{}: {} [OPTION]... [COMMAND]".format (tc.white ("Usage"), sys.argv [0]))
        print ("COMMAND can be one of [{}]".format ('|'.join (COMMANDS)))
        argopt.usage (True)

    cmd = None
    if "-d" in options:
        cmd = "start"
    else:
        for cmd_ in COMMANDS:
            if cmd_ in options.argv:
                cmd = cmd_
                break
    return cmd

def getsysopt (name, default = None):
    try:
        return sys.argv [sys.argv.index ("---{}".format (name)) + 1]
    except ValueError:
        return default

def hassysopt (name):
    return "---{}".format (name) in sys.argv


def sched (interval, func):
    lifetime.maintern.sched (interval, func)

SERVICE_USER = None

def run (**conf):
    import os, sys, time
    from . import Skitai
    from rs4.psutil import flock

    class SkitaiServer (Skitai.Loader):
        NAME = 'instance'

        def __init__ (self, conf):
            global WASC, EVBUS

            self.conf = conf
            self.flock = None
            Skitai.Loader.__init__ (self, 'config', conf.get ('logpath'), conf.get ('varpath'), conf.get ("wasc"))
            WASC = self.wasc
            EVBUS.set_logger (self.wasc.logger.get ('app'))

        def close (self):
            if self.wasc.httpserver.worker_ident == "master":
                pass
            Skitai.Loader.close (self)

        def config_logger (self, path):
            media = []
            if path is not None:
                media.append ("file")
            if self.conf.get ('verbose', "no") in ("yes", "1", 1):
                media.append ("screen")
                self.conf ['verbose'] = "yes"
            if not media:
                media.append ("screen")
                self.conf ['verbose'] = "yes"
            Skitai.Loader.config_logger (self, path, media, self.conf ["log_off"], self.conf.get ('file_loggings'))

        def master_jobs (self):
            skitaienv = os.environ.get ("SKITAIENV")
            if skitaienv == "DEVEL":
                mode = 'development'
            elif skitaienv == "PYTEST":
                mode = 'pytest'
            else:
                mode = 'production'
            self.wasc.logger ("server", "[info] engine is running in {} mode".format (tc.red (mode)))
            self.wasc.logger ("server", "[info] data path is %s" % tc.white (self.varpath))
            if self.logpath:
                self.wasc.logger ("server", "[info] log file path is %s" % tc.white (self.logpath))
            self.set_model_keys (self.conf ["models_keys"])

        def maintern_shutdown_request (self, now):
            req = self.flock.lockread ("signal")
            if not req: return
            self.wasc.logger ("server", "[info] got signal - %s" % req)
            if req == "terminate":
                lifetime.shutdown (0, 30.0)
            elif req == "restart":
                lifetime.shutdown (3, 30.0)
            elif req == "kill":
                lifetime.shutdown (0, 1.0)
            elif req == "rotate":
                self.wasc.logger.rotate ()
            else:
                self.wasc.logger ("server", "[error] unknown signal - %s" % req)
            self.flock.unlock ("signal")

        def configure (self):
            options = argopt.options ()
            start_server = '--collect-static' not in argopt.options ()
            conf = self.conf

            self.wasc.register ('varpath', conf ['varpath'])

            _poll = options.get ('--poll') or conf.get ('poll')
            _poll and use_poll (_poll)

            _tasks = int (options.get ('--tasks') or conf.get ('tasks', 0))
            if _tasks:
                conf ['enable_async'] = _tasks

            workers = int (options.get ('--workers') or conf.get ('workers', 1))
            threads = int (options.get ('--threads') or conf.get ('threads', 4))
            # assert threads, "threads should be more than zero"

            port = int (options.get ('--port') or conf.get ('port', 5000))
            quic = int (options.get ('--quic') or conf.get ('quic', 0))

            self.set_num_worker (workers)
            if conf.get ("certfile"):
                self.config_certification (conf.get ("certfile"), conf.get ("keyfile"), conf.get ("passphrase"))

            self.config_wasc (**conf ['wasc_options'])

            if conf.get ('fws_to'):
                self.config_forward_server (
                    conf.get ('fws_address', '0.0.0.0'),
                    conf.get ('fws_port', 80), conf.get ('fws_to', 443)
                )

            if conf ['background_jobs']:
                import psutil
                procnames = [ proc.name () for proc in psutil.process_iter() ]
                for procname, cmd in conf ['background_jobs']:
                    if procname not in procnames:
                        self.wasc.logger.get ("server").log ('background job {}: {}'.format (tc.yellow (procname), tc.white (cmd)))
                        os.system (cmd + '&')

            if conf ['media_path'] is None:
                conf ['media_path'] = os.path.expanduser (os.path.join ('~/.skitai', conf.get ('name', '.unnamed'), 'pub'))
                pathtool.mkdir (conf ['media_path'])
                mount (conf ['media_url'], conf ['media_path'], first = True)

            self.config_webserver (
                port, conf.get ('address', '0.0.0.0'),
                NAME, conf.get ("certfile") is not None,
                conf.get ('keep_alive', DEFAULT_KEEP_ALIVE),
                conf.get ('network_timeout', DEFAULT_NETWORK_TIMEOUT),
                conf.get ('fws_domain'),
                quic = quic,
                backlog = conf.get ('backlog', 100),
                multi_threaded = threads > 0,
                max_upload_size = conf ['max_upload_size'],
                thunks = [self.master_jobs],
                start = start_server
            )

            if start_server and os.name == "posix" and self.wasc.httpserver.worker_ident == "master":
                # master does not serve
                return

            self.config_executors (
                conf.get ('executors_workers', threads),
                conf.get ("executors_zombie_timeout", DEFAULT_BACKGROUND_TASK_TIMEOUT),
                conf.get ("executors_process_start"),
                conf.get ("enable_async")
            )
            self.config_threads (threads)

            # mount resources ----------------------------
            try:
                self.install_handler (
                    conf.get ("mount"),
                    conf.get ("max_ages", {}),
                    conf ['media_url'],
                    conf ['media_path']
                )

                for p, s in conf ['subscriptions']:
                    try:
                        provider = self.get_app_by_name (p)
                        provider.bus
                        subbscriber = self.get_app_by_name (s).bus
                    except AttributeError:
                        raise NameError ('app.bus not found')

                    provider.add_subscriber (subbscriber)
                    self.wasc.logger.get ("server").log ('app {} subscribes to {}'.format (tc.info (s), tc.cyan (p)))

            except:
                self.wasc.logger.trace ("app")
                if is_devel ():
                    self.wasc.logger.get ("server") ("reboot worker after 10 seconds...", "error")
                    [ time.sleep (1) for _ in range (10) ]
                    os._exit (3)
                else:
                    os._exit (2)

            lifetime.init (logger = self.wasc.logger.get ("server"))
            if os.name == "nt":
                lifetime.maintern.sched (11.0, self.maintern_shutdown_request)
                self.flock = flock.Lock (os.path.join (self.varpath, ".%s" % self.NAME))

    #----------------------------------------------------------------------

    global dconf, PROCESS_NAME, SERVICE_USER, SERVICE_GROUP, Win32Service, STATUS

    STATUS = 'CREATING'
    SERVICE_USER = argopt.options ().get ('--user')
    SERVICE_GROUP = argopt.options ().get ('--group')

    for k, v in dconf.items ():
        if k not in conf:
            conf [k] = v

    if conf.get ("name"):
        PROCESS_NAME = 'sktd:{}'.format (conf ["name"])
    if not conf.get ('mount'):
        raise SystemError ('No mount point')

    conf ["varpath"] = get_varpath (get_proc_title ())
    pathtool.mkdir (conf ["varpath"])
    if "logpath" in conf and not conf ["logpath"]:
        conf ["logpath"] = get_logpath (get_proc_title ())

    cmd = get_command ()
    working_dir = getswd ()
    lockpath = conf ["varpath"]
    servicer = service.Service (get_proc_title(), working_dir, lockpath, Win32Service)
    if cmd and not servicer.execute (cmd, SERVICE_USER, SERVICE_GROUP):
        return
    if not cmd:
        if servicer.status (False):
            raise SystemError ("daemon is running")
        conf ['verbose'] = 'yes'
    elif cmd in ("start", "restart"):
        if conf.get ('logpath'): # not systemd, enable app, server logging
            conf ['file_loggings'] = ['request', 'server', 'app']

    server = SkitaiServer (conf)
    # mount additionals while mounting apps and mount apps
    server.just_before_run (conf.get ("mount_onfly"))
    STATUS = 'CREATED'

    if '--collect-static' in argopt.options ():
        from .wastuff import autoconf

        vhost = server.virtual_host.sites [None]
        autoconf.generate (abspath ('.'), vhost, conf)
        sys.exit ()

    # timeout for fast keyboard interrupt on win32
    try:
        STATUS = 'STARTING'
        try:
            server.run (conf.get ('verbose') and 3.0 or 30.0)
        except KeyboardInterrupt:
            pass
        STATUS = 'STARTED'

    finally:
        _exit_code = server.get_exit_code ()
        if _exit_code is not None: # master process
            sys.exit (_exit_code)
        else:
            # worker process
            # for avoiding multiprocessing.manager process's join error
            os._exit (lifetime._exit_code)
        STATUS = 'STOPPED'
