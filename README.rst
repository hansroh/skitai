===================
Skitai App Engine
===================

At a Glance
=============

Skitai is a Python WSGI/HTTP Server for UNIX (Developing is possible on win32). 
  
And simple to run:

Install, 

.. code:: bash

  pip3 install skitai

Create and mount your app,
  
.. code:: python
  
  # myservice.py

  def app (env, start_response):
    start_response ("200 OK", [("Content-Type", "text/plain")])
    return 'Hello World'

  if __name__ == "__main__":    
    import skitai
    
    skitai.mount ('/', app)
    skitai.run (address = "127.0.0.1", port = 5000)

And run.

.. code:: bash
        
  python3 myservice.py


Your app will work for your thousands or miliions of customers.


.. contents:: Table of Contents


What For
===========

Skitai App engine provides one of most simplest way to:

1. Serve WSGI apps like Flask, Django
2. Export RESTful API for your apps or functions
3. Build high performance app/web service with asynchronous backend upstreams & cache control


Introduce
===========

Skitai is a kind of branch of `Medusa Web Server`__ - A High-Performance Internet Server Architecture. Medusa is different from most other servers because it runs as a single process, multiplexing I/O with its various client and server connections within a single process/thread. 

Skitai orients light-weight, simplicity and strengthen networking operations with your backend resources keeping very low costs.

- Working as WSGI application server, Web, XML-RPC and reverse proxy and loadbancing server
- Handling massive requests to your backend servers including RESTful API, RPCs and database engines - PostgreSQL_, MongoDB and Redis - with asynchronous manner
- HTTP/2.0 & HTML5 Websocket implemented

Skitai is not a just developing server like some frameworks provides. It is supporsed to work fine under real service situation by alone. And it makes your app take off to the world, just by appending a few lines on your app.

For attaining maximum concurrency, it uses:

  - asyncore with event loop for IO concurrency like HTTP/Websocket and database engine connections
  - forking for multiple process workers
  - multi-threading for blocking jobs if you want

Async supported protocols:

  - HTTP/HTTPS, RESTful API and XML/JSON-RPC
  - HTTP2 and GRPC
  - Websocket

Async supported database engine or NoSQL:

  - PostgreSQL
  - MongoDB
  - Redis
  - SQLite3 (sync only, not async )

.. _hyper-h2: https://pypi.python.org/pypi/h2
.. _Flask: http://flask.pocoo.org/
.. _PostgreSQL: http://www.postgresql.org/
.. __: http://www.nightmare.com/medusa/medusa.html


Installation
=========================

**Requirements**

Python 3.5+  

On win32, required `pywin32 binary`_.

.. _`pywin32 binary`: http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/

On posix, for compiling psycopg2 module, requires theses packages,

.. code:: bash
    
  apt-get install libpq-dev python-dev
  
**Installation**

With pip

.. code-block:: bash

    pip3 install skitai    

From git

.. code-block:: bash

    git clone https://gitlab.com/hansroh/skitai.git
    cd skitai
    python3 setup.py install


But generally you don't need install alone. When you install Skitai App Engine, proper version of Skitai App Engine will be installed.


Enginize Your App with Skitai
===============================

Here's a very simple WSGI app,

Basic Usage
------------

Mount Static Directories
````````````````````````````

Your myproject/app.py,

.. code:: python
  
  if __name__ == "__main__": 
  
    import skitai
    
    skitai.mount ('/', '/home/www')
    skitai.mount ('/uploads', '/var/www/uploads')
    skitai.mount ('/uploads/bigfiles', '/data/www/bifgiles')
    
    skitai.run (
      address = "127.0.0.1",      
      port = 5000
    )

At command line,

.. code:: bash

  python3 app.py

For checking processes,
  
.. code:: bash
  
  $ ps -ef | grep skitai
  
  ubuntu   25219     1  0 08:25 ?        00:00:00 skitai(myproject/app): master  
  ubuntu   25221 25219  1 08:25 ?        00:00:00 skitai(myproject/app): worker #0  


Mount WSGI App
```````````````````````

.. code:: python
  
  #WSGI App

  def app (env, start_response):
    start_response ("200 OK", [("Content-Type", "text/plain")])
    return 'Hello World'
    
  app.use_reloader = True
  app.debug = True

  if __name__ == "__main__": 
  
    import skitai
    
    skitai.mount ('/', app)
    skitai.run (
      address = "127.0.0.1",
      port = 5000
    )

At now, run this code from console.

.. code-block:: bash

  python3 app.py

You can access this WSGI app by visiting http://127.0.0.1:5000/.

If you want to allow access to your public IPs, or specify port:

.. code:: python
  
  skitai.mount ('/', app)
  skitai.run (
    address = "0.0.0.0",
    port = 5000
  )

skital.mount () spec is:

mount (mount_point, mount_object, app_name = "app", pref = None)

- mount_point
- mount_object: app, app file path or module object
  
  .. code:: python
  
    skitai.mount ('/', app)
    skitai.mount ('/', 'app_v1/app.py', 'app')
    
    import wissen
    skitai.mount ('/', wissen, 'app')
    skitai.mount ('/', (wissen, 'app_v1.py'), 'app')
    
  In case module object, the module should support skitai exporting spec.
  
- app_name: variable name of app
- pref: run time app config, pref will override app.config


Mount Django App
```````````````````

Basically same as other apps. 

Let's assume your Django app project is '/mydjango' and skitai app engine script is '/app.py'.
   
.. code:: python

  pref = skitai.pref ()
  pref.use_reloader = True
  pref.debug = True
  
  # and mount static dir used bt Django
  skitai.mount ("/static", "mydjango/static")
    
  # finally mount django wsgi.py and project root path to append sys.path by path param.
  skitai.mount (
    "/", 
    "mydjango/mydjango/wsgi.py", 
    "application", 
    pref
  )
  
Note that if app is smae location with django manage.py, you need not path param.

Also note that if you set pref.use_reloader = True, it is possible to replace Django development server (manage,py runserver), But it will work on posix only, because Skitai reloads Django app by restart worker process, Win32 version doesn't support.


Logging and Console Displaying For Developing/Debugging
----------------------------------------------------------

If you do not specify log file path, all logs will be displayed in console, bu specifed all logs will be written into file.

First of all, you should create log directory,

.. code:: bash

  sudo mkdir /var/log/skitai
  sudo chown ubuntu:ubuntu

Your request log file willl be placed to: */var/log/skitai/ubuntu/<script path hash>/request.log*.
  
.. code:: python
  
  skitai.mount ('/', app)
  skitai.enalbe_file_logging ()
  skitai.run (
    address = "0.0.0.0",
    port = 5000
  )

If you also want to view logs through console for spot developing, you run app.py without option.

.. code:: bash

  python3 app.py


Run with Process Name
-------------------------

If you give 'name', process name will be changed.

.. code:: python

  skitai.mount ('/', app)
  skitai.run (name = "myapp")

Your skitai process will be shown as:

.. code:: bash

  ubuntu    9815     1  0 16:04 ?        00:00:00 skitai/myapp: master
  ubuntu    9816  9815  0 16:04 ?        00:00:03 skitai/myapp: worker #0


Getting Command Line Options and Arguments
----------------------------------------------------

Skitai use short options -d, and long options starts with "--skitai-", then you SHOULD NOT use these options.
Also Skitai use satrt, restart, status, stop in args.  then these arguments are removed automatically.

.. code:: python

  opts, args = skitai.argopt ("hf:", ["ssl", "debug", "origin="])
  for k, v in opts:
    if k == "-h":
      ...
    elif k == "-h" or k == "--help":
      usage ()
    elif k == "--debug":
       ...

For detail about get_clopt's parameters, see getopt module.


Run with Threads Pool
------------------------

Skitai run defaultly multi-threading mode and number of threads are 4. 
If you want to change number of threads for handling WSGI app:

.. code:: python

  skitai.mount ('/', app)
  skitai.run (
    threads = 8
  )


Run with Single-Thread
------------------------

If you want to run Skitai with entirely single thread,

.. code:: python
  
  skitai.mount ('/', app)
  skitai.run (
    threads = 0
  )

This features is limited by your WSGI container. If you use Atila_ container, you can run with single threading mode by using Atila_'s async streaming response method. But you don't and if you have plan to use Skitai 'was' requests services, you can't single threading mode and you SHOULD run with multi-threading mode.

.. _Atila: https://pypi.python.org/pypi/atila

Run with Multiple Workers
---------------------------

*Available on posix only*

Skitai can run with multiple workers(processes) internally using fork for socket sharing.

.. code:: python
  
  skitai.mount ('/', app)
  skitai.run (
    port = 5000,
    workers = 4,
    threads = 8
  )

Skitai processes are,
  
.. code:: bash
  
  $ ps -ef | grep skitai
  
  ubuntu   25219     1  0 08:25 ?        00:00:00 skitai(myproject/app): master  
  ubuntu   25221 25219  1 08:25 ?        00:00:00 skitai(myproject/app): worker #0  
  ubuntu   25222 25219  1 08:25 ?        00:00:00 skitai(myproject/app): worker #1  
  ubuntu   25223 25219  1 08:25 ?        00:00:00 skitai(myproject/app): worker #2
  ubuntu   25224 25219  1 08:25 ?        00:00:00 skitai(myproject/app): worker #3


Set Critical Point to Worker Processes
``````````````````````````````````````````
 
*New In Version 0.26.15.2, Available only on posix*

You can set parameters for restarting overloaded workers,
 
.. code:: python

  skitai.set_worker_critical_point (cpu_percent = 90.0, continuous = 3, interval = 20)
  
This means if a worker's CPU usage is 90% for 20 seconds continuously 3 times, Skitai try to kill this worker and start a new worker.

If you do not want to use this, you just do not call set_worker_critical_point () or set interval to zero (0).

But I strongly recommend use this setting especially if you running Sktiai on single CPU processor machine or like AWS t1.x limited computing instances. Also this is for minimum protection against Skitai's unexpected bugs.

  
Mount Multiple WSGI Apps And Static Directories
------------------------------------------------

Skitai can mount multiple WSGI apps.


Independent Apps and Various WSGI Containers
`````````````````````````````````````````````````````

Here's three WSGI app samples:

.. code:: python
  
  # WSGI App

  def app (env, start_response):
    start_response ("200 OK", [("Content-Type", "text/plain")])
    return ['Hello World']
    
  app.use_reloader = True
  app.debug = True


  # OR Flask App
  from flask import Flask  
  app = Flask(__name__)  
  
  app.use_reloader = True
  app.debug = True
  
  @app.route("/")
  def index ():   
    return "Hello World"


  # OR Atila App  
  from atila import Atila  
  app = Atila (__name__)
  
  app.use_reloader = True
  app.debug = True
    
  @app.route('/')
  def index (was):   
    return "Hello World"


Then place this code at bottom of above WSGI app.

.. code:: python
  
  if __name__ == "__main__": 
  
    import skitai
    
    skitai.mount ('/', __file__, 'app')
    skitai.mount ('/', 'static')
    skitai.run ()


Service Versioning
````````````````````
    
These feature can be used for managing versions. 

Let's assume initial version of app file is app_v1.py.

.. code:: python  

  app = Atila (__name__)
    
  @app.route('/')
  def index (was):   
    return "Hello World Ver.1"

And in same directory 2nd version of app file is app_v2.py.

.. code:: python  

  app = Atila (__name__)
      
  @app.route('/')
  def index (was):   
    return "Hello World Ver.2"
  
Now service.py is like this:

.. code:: python

  import skitai
    
  skitai.mount ('/', 'static')
  skitai.mount ('/v1', 'app_v1')  
  skitai.mount ('/v2', 'app_v2')
  skitai.run ()

Then run with:

.. code:: bash

  python service.py
  
  
You can access ver.1 by http://127.0.0.1:5009/v1/ and vwe.2 by http://127.0.0.1:5009/v2/.

Note: Above 3 files is in the same directory and then both share templates directory. If you intend to seperate from app_v1 and app_v2, you should seperate app with directory like this:


.. code:: bash

  service.py

  app_v1/app.py
  app_v1/templates
  app_v1/static

  app_v2/app.py
  app_v2/templates
  app_v2/static


and your service.py:

.. code:: python

  import skitai
  
  skitai.mount ('/v1', 'app_v1/static'),
  skitai.mount ('/v1', 'app_v1/app'),
  skitai.mount ('/v2', 'app_v2/static'),
  skitai.mount ('/v2', 'app_v2/app')        
  skitai.run ()
 

Mounting With Virtual Host
-------------------------------

.. code:: python
  
  if __name__ == "__main__": 
  
    import skitai
    skitai.mount ('/', 'site1.py', host = 'www.site1.com')
    skitai.mount ('/', 'site2.py', host = 'www.site2.com')
    skitai.run ()

Setting POST Body Size Limitation
------------------------------------

For setting 8 Gbytes limitation for POST body size,

.. code:: python
  
  import skitai
  
  pref = skitai.pref ()  
  pref.max_client_body_size = 2 << 32
  
If you want to set more detaily,
  
.. code:: python
  
  import skitai
  
  pref = skitai.pref ()
  
  pref.config.max_post_body_size = 2 << 32
  pref.config.max_multipart_body_size = 2 << 32
  pref.config.max_upload_file_size = 2 << 32
  

Setting Timeout
-----------------

Keep alive timeout means seconds gap of each requests. For setting HTTP connection keep alive timeout,

.. code:: python
  
  skitai.set_keep_alive (2) # default = 30
  skitai.mount ('/', app)
  skitai.run ()
  
If you intend to use skitai as backend application server behind reverse proxy server like Nginx, it is recommended over 300.

Request timeout means seconds gap of data packet recv/sending events,

.. code:: python
  
  skitai.set_request_timeout (10) # default = 30
  skitai.mount ('/', app)
  skitai.run ()

Note that under massive traffic situation, meaning of keep alive timeout become as same as request timeout beacuse a clients requests are delayed by network/HW capability unintensionally.

Anyway, these timeout values are higher, lower response fail rate and longger response time. But if response time is over 10 seconds, you might consider loadbalancing things. Skitai's default value 30 seconds is for lower failing rate under extreme situation.

*New in version 0.26.15*

You can set connection timeout for your backends. Basue of Skitai's ondemend polling feature, it is hard to know disconnected by server side, then Skitai will forcley reconnect if over backend_keep_alive after last interaction. Make sure your backends keep_alive setting value is matched with this value.

.. code:: python
  
  skitai.set_backend_keep_alive (1200) # default is 10
  skitai.mount ('/', app)
  skitai.run ()



Enabling HTTP/HTTPS Proxy
---------------------------

Make sure you really need proxy.

.. code:: python
  
  skitai.enable_proxy ()
    
  # tunnel value will be applied to HTTPS proxy
  skitai.set_proxy_keep_alive (channel = 60, tunnel = 600)
  
  skitai.run ()


Run as Daemon
--------------

*Available on posix only*

For making a daemon,

.. code:: bash
  
  python3 app.py start (or -d)
  
  
For stopping daemon,

.. code:: bash
  
  python3 app.py stop (or -s)

Or for restarting daemon,
  
.. code:: bash
  
  python3 app.py restart (or -r)
  

For automatic starting on system start, add a line to /etc/rc.local file like this:

.. code:: bash

  su - ubuntu -c "/usr/bin/python3 /home/ubuntu/app.py -d"
  
  exit 0

Run as Win32 Service
-----------------------

*Available on win32 only, New in version 0.26.7*

.. code:: python

  from atila import Atila
  from rs4.psutil.win32service import ServiceFramework
  
  class ServiceConfig (ServiceFramework):
    _svc_name_ = "SAE_EXAMPLE"
    _svc_display_name_ = "Skitai Example Service"
    _svc_app_ = __file__
    _svc_python_ = r"c:\python34\python.exe"
  
  app = Atila (__name__)
  
  if __name__ == "__main__":
    skitai.mount ('/', app)
    skitai.set_service (ServiceConfig)
    skitai.run ()

Then at command line,

.. code:: bash

  app.py install # for installing windows service
  app.py start
  app.py stop
  app.py update # when service class is updated
  app.py remove # removing from windwos service
  
Adding Backend Server Alias
----------------------------

Backend server can be defined like this: (alias_type, servers, role = "", source = "", ssl = False).

alias_types can be one of these:
  
  - All of HTTP based services like web, RPC, RESTful API
  
    - PROTO_HTTP
    - PROTO_HTTPS
  
  - Websocket  
    
    - PROTO_WS: websocket
    - PROTO_WSS: SSL websocket
  
  - Database Engines
    
    - DB_PGSQL
    - DB_SQLITE3
    - DB_REDIS
    - DB_MONGODB
    - DJANGO: mount django database engine of settings.py if database engine is PostgreSQL or SQLite3

- server: single or server list, server form is [ username : password @ server_address : server_port / database_name weight ]. if your username or password contains "@" characters, you should replace to '%40'
- role (optional): it is valid only when cluster_type is http or https for controlling API access
- source (optional): comma seperated ipv4/mask
- ssl (optional): use SSL connection or not, PROTO_HTTPS and PROTO_WSS use SSL defaultly

Some examples,

.. code:: python
  
  skitai.alias (
    '@members', 
    skitai.PROTO_HTTP, 
    [ "username:password@members.example.com:5001" ],
    role = 'admin', 
    source = '172.30.1.0/24,192.168.1/24'
  )
  
  skitai.alias (
    '@mypostgres',
    skitai.DB_POSTGRESQL, 
    [
      "postgres:1234@172.30.0.1:5432/test 20",
      "postgres:1234@172.30.0.2:5432/test 10"
    ]
  )
  
  skitai.alias (
    '@mysqlite3',
    skitai.DB_SQLITE3, 
    [
      "/var/tmp/db1",
      "/var/tmp/db2"
    ]
  )


Run as HTTPS Server
---------------------

To generate self-signed certification file:

.. code:: python
  
  ; Create the Server Key and Certificate Signing Request
  sudo openssl genrsa -des3 -out server.key 2048
  sudo openssl req -new -key server.key -out server.csr
  
  ; Remove the Passphrase If you need
  sudo cp server.key server.key.org
  sudo openssl rsa -in server.key.org -out server.key
  
  ; Sign your SSL Certificate
  sudo openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt

Then,

.. code:: python
  
  skitai.mount ('/', app)
  skitai.enable_ssl ('server.crt', 'server.key', 'your pass phrase')
  skitai.run ()

If you want to redirect all HTTP requests to HTTPS,

.. code:: python
  
  skitai.enable_forward (80, 443)
  
  skitai.mount ('/', app)
  kitai.enable_ssl ('server.crt', 'server.key', 'your pass phrase')
  skitai.run (port = 443)


About Mount Point & App Routing
--------------------------------

If app is mounted to '/flaskapp',

.. code:: python
   
  from flask import Flask    
  app = Flask (__name__)       
  
  @app.route ("/hello")
  def hello ():
    return "Hello"

Above /hello can called, http://127.0.0.1:5000/flaskapp/hello

Also app should can handle mount point. 
In case Flask, it seems 'url_for' generate url by joining with env["SCRIPT_NAME"] and route point, so it's not problem. Atila can handle obiously. But I don't know other WSGI containers will work properly.

Run Server Helpers
--------------------

SMTP Delivery Agent
````````````````````````

*New in version 0.26*

e-Mail sending service is executed seperated system process not threading. Every e-mail is temporary save to file system, e-Mail delivery process check new mail and will send. So there's possibly some delay time.

You can send e-Mail in your app like this:

.. code:: python

    # email delivery service
    e = was.email (subject, snd, rcpt)
    e.set_smtp ("127.0.0.1:465", "username", "password", ssl = True)
    e.add_content ("Hello World<div><img src='cid:ID_A'></div>", "text/html")
    e.add_attachment (r"001.png", cid="ID_A")
    e.send ()

With asynchronous email delivery service, can add default SMTP Server. If it is configured, you can skip e.set_smtp(). But be careful for keeping your smtp password.

.. code:: bash
  
  skitai smtpda -d

All e-mails are saved into *varpath* and varpath is not specified default is /var/temp/skitai


Run With Config File
````````````````````````
*New in version 0.26.17*

Both of SMTP and Taks Scheduler can be run with config file, it may be particulary useful in case you run multiple skitai instances. 

.. code:: bash
  
  # ~/.skitai.conf
  
  [smtpda]
  verbose = false
  max-retry = 10
  keep-days = 1
  smtp-server = [your SMTP server]
  user = [your SMTP user name if you need]
  password = [your SMTP user password if you need]
  ssl = true
  
  
And run scripts mannually,
  
.. code:: bash

  skitai smtpda
    
.. code:: bash

  Options:
  
    start: start as daemon
    restart
    stop
    status
  
  Example:
  
    skitai smtpda status
    skitai smtpda restart  
  
I you give cammnad line options, theses have more priority than config file.

And for running automatically on system boot, you can add this line to /etc/rc.local like this,

.. code:: bash

  # /etc/rc.local
  
  su - ubuntu -c "/usr/local/bin/skitai smtpda start"

In this case, smtpda will use spool directory at */tmp/skitai/smtpda*, so your each apps SHOULD NOT call *skitai.smtpda ()* if you want to share spool directory.


Asccessing File Resources On Startup
--------------------------------------

Skitai's working directory is where the script call skitai.run (). Even you run skitai at root directory,

.. code:: bash

  /app/example/app.py -d
  
Skitai will change working directory to /app/example on startup.

So your file resources exist within skitai run script, you can access them by relative path,

.. code:: python
  
  monitor = skital.abspath ('package', 'monitor.py')  

Also, you need absolute path on script,

.. code:: python

  skitai.getswd () # get skitai working directory


Enable Cache File System
------------------------------

If you make massive HTTP requests, you can cache contents by HTTP headers - Cache-Control and Expires. these configures will affect to 'was' request services, proxy and reverse proxy.

.. code:: python
  
  skitai.enable_cachefs (memmax = 10000000, diskmax = 100000000, path = '/var/tmp/skitai/cache')
  skitai.mount ('/', app)
  skitai.run ()

Default values are:

- memmax: 0
- diskmax: 0
- path: None

 
Configure Max Age For Static Files
--------------------------------------
  
You can set max-age for static files' respone header like,

.. code:: bash

  Cache-Control: max-age=300
  Expires: Sun, 06 Nov 2017 08:49:37 GMT

If max-age is only set to "/", applied to all files. But you can specify it to any sub directories.

.. code:: python

  skitai.mount ('/', 'static')
  skitai.set_max_age ("/", 300)
  skitai.set_max_age ('/js', 0)
  skitai.set_max_age ('/images', 3600)
  skitai.run ()

Enable Cache File System
------------------------------

If you make massive HTTP requests, you can cache contents by HTTP headers - Cache-Control and Expires

.. code:: python
  
  skitai.enable_cachefs (path = '/var/skitai/cache', memmax = 0, diskmax = 0)
  skitai.mount ('/', app)
  skitai.run ()


Enabling API Gateway Server
-----------------------------

Using Skitai's reverse proxy feature, it can be used as API Gateway Server. All backend API servers can be mounted at gateway server with client authentification and transaction ID logging feature.

.. code:: python

  class Authorizer:
    def __init__ (self):
      self.tokens = {
        "12345678-1234-123456": ("hansroh", ["user", "admin"], 0)
      }
      
    # For Token
    def handle_token (self, handler, request):
      username, roles, expires = self.tokens.get (request.token)
      if expires and expires < time.time ():
        # remove expired token
        self.tokens.popitem (request.token)
        return handler.continue_request (request)
      handler.continue_request (request, username, roles)
    
    # For JWT Claim
    def handle_claim (self, handler, request):
      claim = request.claim    
      expires = claim.get ("expires", 0)
      if expires and expires < time.time ():
        return handler.continue_request (request)
      handler.continue_request (request, claim.get ("user"), claim.get ("roles"))
    
  @app.before_mount
  def before_mount (wac):
    wac.handler.set_auth_handler (Authorizer ())
    
  @app.route ("/")
  def index (was):
    return "<h1>Skitai App Engine: API Gateway</h1>"
  
  
  if __name__ == "__main__":
    import skitai
    
    skitai.alias (
      '@members', 'https', "members.example.com", 
      role = 'admin', source = '172.30.1.0/24,192.168.1/24'  
    )
    skitai.alias (
      '@photos', skitai.DB_SQLITE3, ["/var/tmp/db1", "/var/tmp/db2"]
    )
    skitai.mount ('/', app)
    skitai.mount ('/members', '@members')
    skitai.mount ('/photos', '@photos')      
    skitai.enable_gateway (True, "8fa06210-e109-11e6-934f-001b216d6e71")
    skitai.run ()
    
Gateway use only bearer tokens like OAuth2 and JWT(Json Web Token) for authorization. And token issuance is at your own hands. But JWT creation, 

.. code:: python

  from aquests.lib import jwt
  
  secret_key = b"8fa06210-e109-11e6-934f-001b216d6e71"
  token = jwt.gen_token (secret_key, {'user': 'Hans Roh', 'roles': ['user']}, "HS256")

Also Skitai create API Transaction ID for each API call, and this will eb explained in Skitai 'was' Service chapter.


Using Database Engine For Verifying Token
```````````````````````````````````````````

*New in version 0.24.8*

If you are not familar with Skitai 'was' request services, it would be better to skip and read later.

You can query for getting user information to database engines asynchronously. Here's example for MongDB.

.. code:: python
  
  from skitai import was
  
  class Authorizer:  
    def handle_user (self, response, handler, request):
      username = response.data ['username']
      roles = response.data ['roles']
      expires = response.data ['expires']
      
      if expires and expires < time.time ():
        was.mongodb (
          "@my-mongodb", "mydb", callback = lambda x: None,
        ).delete ('tokens', {"token": request.token})
        handler.continue_request (request)
      else: 
        handler.continue_request (request, username, roles)
          
    def handle_token (self, handler, request):
      was.mongodb (
        "@my-mongodb", "mydb", callback = (self.handle_user, (handler, request))
      ).findone ('tokens', {"token": request.token})


Request Logging
-----------------

Turn Request Logging Off For Specific Path
`````````````````````````````````````````````

For turn off request log for specific path, 

.. code:: python

  # turned off starting with
  skitai.log_off ('/static/')
  
  # turned off ending with
  skitai.log_off ('*.css')
  
  # you can multiple args
  skitai.log_off ('*.css', '/static/images/', '/static/js/')


Log Format
````````````

Blank seperated items of log line are,

- log date
- log time
- client ip or proxy ip

- request host: default '-' if not available
- request methods
- request uri
- request version
- request body size

- reply code
- reply body size

- global transaction ID: for backtracing request if multiple backends related
- local transaction ID: for backtracing request if multiple backends related
- username when HTTP auth: default '-', wrapped by double quotations if value available
- bearer token when HTTP bearer auth

- referer: default '-', wrapped by double quotations if value available
- user agent: default '-', wrapped by double quotations if value available
- x-forwared-for, real client ip before through proxy

- Skitai engine's worker ID like M(Master), W0, W1 (Worker #0, #1,... Posix only)
- number of active connections when logged, these connections include not only clients but your backend/upstream servers
- duration ms for request handling
- duration ms for transfering response data


Testing Mounted App
``````````````````````````````````````

*New in version 0.27*

For mounted app testing fully network environment,

.. code:: python

  import skitai
  
  def test_myapp ():
    with skitai.test_client ("./app.py", 6000) as cli:
      resp = cli.get ("/")
      assert "something" in resp.text    
      
      # api call
      stub = cli.api ()
      resp = stub.apis.pets (45).get ()
      assert resp.data ["id"] == 45

Now run pytest.    

This test client will start Skitai server on port 6000 with app. app.py shoud have skitai.run ().

Note: Port that skitai.run (port = 5000) will be ignored, app.py will be launched with port 6000 that specified by skitai.test_client for avoiding exist app service. 


If your have so many tests, define cli at your conftest.py

.. code:: python

  import pytest
  import skitai
  
  @pytest.fixture (scope = "session")
  def cli ():
    c = skitai.test_client ("./app.py", 6000)
    yield c
    c.stop ()

And edit your test script:

.. code:: python

  import skitai
  
  def test_myapp (cli):    
    resp = cli.get ("/")
    assert "something" in resp.text    
    
    # api call
    stub = cli.api ()
    resp = stub.apis.pets (45).get ()
    assert resp.data ["id"] == 45


If you run test server at another console window for watching server error messages, give dry = True parameter.

.. code:: python

  @pytest.fixture (scope = "session")
  def cli ():
    c = skitai.test_client ("./app.py", 5000, dry = True)
    yield c
    c.stop ()

This test client will not start Skitai server but access to port 5000 so you start server manually at another console,

.. code:: bash

  python3 app.py


Skitai with Nginx
---------------------------

Here's some helpful sample works with Nginx.

.. code:: python
    
  # use http 1.1 for backends
  proxy_http_version 1.1;  
  proxy_set_header Host $host;
  proxy_set_header X-NginX-Proxy true;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  
  # enabling websocket
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "Upgrade";
  proxy_read_timeout 86400;
  
  # upstreams with connection keep alive    
  upstream backend {
    server 127.0.0.1:5000;
    keepalive 100;
  }
  
  server {
    listen 80;
    server_name www.oh-my-jeans.com;    
	  keepalive_timeout 30s;
	
    location / {    
      proxy_pass http://backend;
      add_header X-Backend "skitai app engine";
      client_max_body_size 2g;
    }
    
    location /assets/ {
      alias /home/ubuntu/www/statics/assets/;
      expires 86400;    
    }
  }


Self-Descriptive App
---------------------

Skitai's one of philasophy is self-descriptive app. This means that you once make your app, this app can be run without any configuration or config files (at least, if you need own your resources/log files directoring policy). Your app contains all configurations for not only its own app but also Skitai. As a result, you can just install Skitai with pip, and run your app.py immediately.

.. code:: bash

  pip3 install skitai
  # if your app has dependencies
  pip3 install -Ur requirements.txt
  python3 app.py

Skitai App Examples
---------------------

Also please visit to `Skitai app examples`_.

.. _`Skitai app examples`: https://gitlab.com/hansroh/skitai/tree/master/tests/examples



Export API From Your Module Through Skitai
=============================================

If your module need export APIs or web pages, you can include app in your module for Skitai App Engine.

Let's assume your package name is 'unsub'.

Your app should be located at unsub/export/skitai/__export__.py

Then users uses your module can mount on skitai by like this,

.. code:: python
  
  import unsub
  
  pref = skitai.pref ()  
  pref.config.urlfile = skitai.abspath ('resources', 'urllist.txt')
  
  skitai.mount ("/v1", unsub, "app", pref)
  skitai.run ()
  
If you want to specify filename like app_v1.py for version management,

.. code:: python
  
  skitai.mount ("/v1", (unsub, "app_v1.py"), "app", pref)
  

If your app need bootstraping or capsulizing complicated initialize process from simple user settings, write code to unsub/export/skitai/__init__.py.

.. code:: python
  
  import skitai
  
  def bootstrap (pref):    
    with open (pref.config.urlfile, "r") as f:
      urllist = [] 
      while 1:
        line = f.readline ().strip ()
        if not line: break
        urllist.append (line.split ("  ", 4))
      pref.config.urllist = urllist  
     
 *Important Note:* You should add zip_safe = False flag in your setup.py because Skitai could access your __export__ script and its sub modules. 
 
.. code:: python

  setup (
    name = "mymodule",
    ...
    zip_safe = False
  )  
 
 
Examples
----------

Here're some implementations I made.

- `DeLune API Server`_ 
- `Haiku API Server`_
- `Tensorflow API Server`_

.. _`DeLune API Server`: https://pypi.python.org/pypi/delune
.. _`Tensorflow API Server`: https://pypi.python.org/pypi/tfserver
.. _`Haiku API Server`: https://pypi.python.org/pypi/haiku-lst


Skitai 'was' Services
=======================

'was' means (Skitai) *WSGI Application Support*. 

WSGI container like Flask, need to import 'was':

.. code:: python

  from skitai import was
  
  @app.route ("/")
  def hello ():
    was.get ("http://...")
    ...    

But Atila WSGI container integrated with Skitai, use just like Python 'self'.

It will be easy to understand think like that:

- Skitai is Python class instance
- 'was' is 'self' which first argument of instance method
- Your app functions are methods of Skitai instance

.. code:: python
  
  @app.route ("/")
  def hello (was, name = "Hans Roh"):
    was.get ("http://...")
    ...

Simply just remember, if you use WSGI container like Flask, Bottle, ... - NOT Atila - and want to use Skitai asynchronous services, you should import 'was'. Usage is exactly same. But for my convinient, I wrote example codes Atila version mostly.


Async Communication For Backends To Backends
------------------------------------------------------

Most importance service of 'was' is making requests to HTTP, REST, RPC and several database engines. And this is mostly useful for fast Server Side Rendering with outside resources.

Recently Javascript provides good asynchronous communicating tools like AJAX or axios.js for **frontends - backends**. Like this, 'was' provides **backends - backends** communicating tool.

The modules is related theses features from aquests_ and you could read aquests_ usage first.

I think it just fine explains some differences with aquests.

First of all, usage is somewhat different because aquests is used within threadings on skitai. Skitai takes some threading advantages and compromise with them for avoiding callback heaven.

API Calling
`````````````````````````````

At aquests,

.. code:: python

  import aquests
  
  def display_result (response):
    print (reponse.data)
  
  aquests.configure (callback = display_result, timeout = 3)
    
  aquests.get (url)
  aquests.post (url, {"user": "Hans Roh", "comment": "Hello"})
  aquests.fetchall ()

At Skitai,
  
.. code:: python
  
  @app.route (...)
  def request (was):
    req1 = was.get (url)
    req2 = was.post (url, {"user": "Hans Roh", "comment": "Hello"})    
    respones1 = req1.getwait (timeout = 3)
    response2 = req2.getwait (timeout = 3)    
    return [respones1.data, respones2.data]

The significant differnce is calling getwait (timeout) for getting response data.

Database Querying
`````````````````````````````

PostgreSQL query at aquests,

.. code:: python

  import aquests
  
  def display_result (response):
    for row in response.data:
      row.city, row.t_high, row.t_low
  
  aquests.configure (callback = display_result, timeout = 3)
  
  dbo = aquests.postgresql ("127.0.0.1:5432", "mydb")
  dbo.excute ("SELECT city, t_high, t_low FROM weather;")
  aquests.fetchall ()

At Skitai,

.. code:: python
  
  @app.route (...)  
  def query (was):
    dbo = was.postgresql ("127.0.0.1:5432", "mydb")
    s = dbo.excute ("SELECT city, t_high, t_low FROM weather;")
    
    response = s.getwait (2)
    for row in response.data:
      row.city, row.t_high, row.t_low


If you needn't returned data and just wait for completing query,

.. code:: python

    dbo = was.postgresql ("127.0.0.1:5432", "mydb")
    req = dbo.execute ("INSERT INTO CITIES VALUES ('New York');")
    req.wait (2) 

If failed, exception will be raised.

gRCP Calling
```````````````````

For another gRPC example, calling to tfserver_ for predicting something with tensorflow model. 
  
.. code:: python

  from tfserver import cli 
  
  @app.route (...)  
  def predict_grpc (was):
    stub = was.grpc ("http://127.0.0.1:5000/tensorflow.serving.PredictionService")	
    fftseq = getone ()
    request = cli.build_request ('model', 'predict', stuff = fftseq)
    req = stub.Predict (request, 10.0)
    resp = req.getwait ()
    return cli.Response (resp.data).y  

Here're addtional methods and properties above response obkect compared with aquests' response one.

- cache (timeout): response caching
- status: it indicate requests processed status and note it is not related response.status_code.

  - 0: Initial Default Value
  - 1: Operation Timeout
  - 2: Exception Occured
  - 3: Normal Terminated

.. _aquests: https://pypi.python.org/pypi/aquests
.. _tfserver: https://pypi.python.org/pypi/tfserver


Methods List
````````````````

All supoorted request methods are:

- Web/API related

  - was.get ()
  - was.delete ()
  - was.post ()
  - was.put ()
  - was.patch ()
  - was.upload ()
  - was.options ()

Above request type is configured to json. This mean request content type and response accept type is all 'application/json'.

If you want to change default value,

1. set app.config.default_request_type = (request content type, accept content type)

.. code:: python

  app.config.default_request_type = ("text/xml", "*/*")
  
2. use headers paramter for each request:

.. code:: python

  req = was.get ("@delune/documents/11", headers = [("Accept", "text/xml")])

  data = {"Title": "...", "Content": "..."}
  headers = [
    ("Content-Type", "application/x-www-form-urlencoded"), 
    ("Accept", "text/xml")
  ]
  req = was.post ("@delune/documents", data, headers = headers)  

- RPCs
  
  - was.rpc (): XMLRPC
  - was.grpc (): gRPC

- Database Engines
  
  - was.postgresql ()
  - was.mongodb ()
  - was.redis ()
  - was.sqlite3 ()
  - was.backend (): if you make alias for your database, you needn't specify db type, just use backend ()
  
- Websocket
  
  - was.ws ()
  - was.wss ()


Usage At Single Threaded Environment
`````````````````````````````````````

If you run Skitai with single threaded mode, you can't use req.wait(), req.dispatch(). Instead you should use callback for this, and Skitai provide async response.

.. code:: python
  
  def promise_handler (promise, response):
    promise.settle (response.content)
        
  @app.route ("/index")
  def promise_example (was):
    promise = was.promise (promise_handler)    
    promise.get (None, "https://pypi.python.org/pypi/skitai")    
    return promise

Unfortunately this feature is available on Atila WSGI container only (It means Flask or other WSGI container users can only use Skitai with multi-threading mode). 

For more detail usage will be explained 'Atila Async Streaming Response' chapter and you could skip now.


Load-Balancing
````````````````

Skitai support load-balancing requests.

If server members are pre defined, skitai choose one automatically per each request supporting *fail-over*.

Then let's request XMLRPC result to one of mysearch members.
   
.. code:: python

  @app.route ("/search")
  def search (was, keyword = "Mozart"):
    s = was.rpc.lb ("@mysearch/rpc2").search (keyword)
    results = s.dispatch (5)
    return result.data
  
  if __name__ == "__main__":
    import skitai
    
    skitai.alias (
      '@mysearch',
       skitai.PROTO_HTTPS, 
       ["s1.myserver.com", "s2.myserver.com"]
    )
    skitia.mount ("/", app)
    skitai.run ()
  
  
It just small change from was.rpc () to was.rpc.lb ()

*Note:* If @mysearch member is only one, was.get.lb ("@mydb") is equal to was.get ("@mydb").

*Note2:* You can mount cluster @mysearch to specific path as proxypass like this:

.. code:: bash
  
  if __name__ == "__main__":
    import skitai
    
    skitai.alias (
      '@mysearch',
       skitai.PROTO_HTTPS, 
       ["s1.myserver.com", "s2.myserver.com:443"]
    )
    skitia.mount ("/", app)
    skitia.mount ("/search", '@mysearch')
    skitai.run ()
  
It can be accessed from http://127.0.0.1:5000/search, and handled as load-balanced proxypass.

This sample is to show loadbalanced querying database.
Add mydb members to config file.

.. code:: python

  @app.route ("/query")
  def query (was, keyword):
    dbo = was.postgresql.lb ("@mydb")    
    req = dbo.execute ("SELECT * FROM CITIES;")
    result = req.dispatch (2)
  
   if __name__ == "__main__":
    import skitai
    
    skitai.alias (
      '@mydb',
       skitai.PGSQL, 
       [
         "s1.yourserver.com:5432/mydb/user/passwd", 
         "s2.yourserver.com:5432/mydb/user/passwd"
       ]
    )
    skitia.mount ("/", app)
    skitai.run ()
    

Map-Reducing
``````````````

Basically same with load_balancing except Skitai requests to all members per each request.

.. code:: python

  @app.route ("/search")
  def search (was, keyword = "Mozart"):
    stub = was.rpc.map ("@mysearch/rpc2")
    req = stub.search (keyword)
    results = req.dispatch (2)
    
    all_results = []
    for result in results:      
       all_results.extend (result.data)
    return all_results

There are 2 changes:

1. from was.rpc.lb () to was.rpc.map ()
2. results is iterable


More About Fetching Result
``````````````````````````````````````

- ClusterDistCall.wait (timeout = 10, reraise = True)
- ClusterDistCall.dispatch (timeout = 10, reraise = False, cache = None, cache_if = (200,))
- ClusterDistCall.wait_or_throw (timeout = 10)
- ClusterDistCall.dispatch_or_throw (timeout = 10, cache = None, cache_if = (200,))
- ClusterDistCall.data_or_throw (timeout = 10, cache = None, cache_if = (200,))

Using Aliased Database
``````````````````````````

If you have alias your database server, you needn't specify db type like 'dbo = was.postgresql ("@mydb")'. Just use 'dbo = was.backend ("@mydb")'.

It makes easy to handle both Sqlite3 and PostgreSQL. If you intend to use Sqlite3 at developing, but use PostgreSQL at production, you just change alias on Skitai startup time.


Using SQLAlchemy Query Generator
````````````````````````````````````````````````

If you use sqlalchemy_ for database ORM, you cannot use ORM itself but use for gfenerating SQL query statement.

.. code:: python
  
  # models.py
  
  from sqlalchemy.ext.declarative import declarative_base
  from sqlalchemy import MetaData, Table
  from sqlalchemy import Column, Integer, String
  
  Base = declarative_base ()
  
  class Stocks (Base):
    __tablename__ = 'stocks'
    id = Column(Integer, primary_key=True)
    date = Column(String(255))
    trans = Column(String(255))
    symbol = Column(String(255))
    qty = Column(Integer)
    price = Column(Integer)
  stocks = Stocks.__table__

Or,

.. code:: python
  
  # models.py  
  
  metadata = MetaData()
  stocks = Table ('stocks', metadata,
     Column('id', Integer, primary_key=True),
     Column('date', String(255)),
     Column('trans', String(255)),
     Column('symbol', String(255)),
     Column('qty', Integer),
     Column('price', Integer)
  )

For generating query statements,

.. code:: python
  
  from models import stocks
  
  @app.route ("/q/<int:id>)
  def q (was, id):
    statement = stocks.select().where(stocks.c.id == id)
    res = was.backend ("@mydb").execute (statement).dispatch ()
    res.data
    ...
    
Other simple query examples,

.. code:: python    
    
  statement = stocks.insert().values (id = 2, date = '2019-1-30', trans = "SELL", symbol = "APL", qty = 200, price = 1600.0)
  statement = stocks.delete().where(stocks.c.id == 2)
  statement = stocks.update().values(symbol='BIX').where(stocks.c.id == 2)
  
For more information about query generating, visit `SQLAlchemy Core`_.    

.. _sqlalchemy: https://www.sqlalchemy.org/
.. _`SQLAlchemy Core`: https://docs.sqlalchemy.org/en/latest/core/index.html


Throwing HTTP Error On Request Failed
`````````````````````````````````````````

*Available only on Atila*

For throwing HTTP error if request is failed immediately,

.. code:: python

  result = req.dispatch_or_throw ("500 Internal Server Error", 10) # 2nd param is timeout

This code abort to handle request and return HTTP 500 error immediatley.


Caching Result
````````````````

By default, all HTTP requests keep server's cache policy given by HTTP response header (Cache-Control, Expire etc). But you can control cache as your own terms including even database query results.

Every results returned by dispatch() can cache.

.. code:: python

  s = was.rpc.lb ("@mysearch/rpc2").getinfo ()
  result = s.dispatch (2)
  if result.status_code == 200:
    result.cache (60) # 60 seconds
  
  s = was.rpc.map ("@mysearch/rpc2").getinfo ()
  results = s.dispatch (2)
  # assume @mysearch has 3 members
  if results.status_code == [200, 200, 200]:
    result.cache (60)

Although code == 200 alredy implies status == 3, anyway if status is not 3, cache() will be ignored. If cached, it wil return cached result for 60 seconds.

*New in version 0.15.28*

If you dispatch with reraise argument, code can be simple.

.. code:: python

  s = was.rpc.lb ("@mysearch/rpc2").getinfo ()
  content = s.dispatch (2, reraise = True).data
  s.cache (60)

Please note cache () method is both available request and result objects.

You can control number of caches by your system memory before running app.

.. code:: python
  
  skitai.set_max_rcache (300)
  skitai.mount ('/', app)
  skitai.run ()

*New in version 0.14.9*

For expiring cached result by updating new data:

.. code:: python
  
  refreshed = False
  if was.request.command == "post":
    ...
    refreshed = True
  
  s = was.rpc.lb (
    "@mysearch/rpc2", 
    use_cache = not refreshed and True or False
  ).getinfo ()
  result = s.dispatch (2)
  if result.status_code == 200:
    result.cache (60) # 60 seconds  

*New in version 0.27*

You can cache with dispatch,

For expiring cached result by updating new data:

.. code:: python
  
  s = was.rpc.lb (
    "@mysearch/rpc2", 
    use_cache = not refreshed and True or False
  ).getinfo ()
  result = s.dispatch (2, cache = 60)
  
*Note* that In this case, it is cached only *if status_code is 200*. If you want cache for another status_code, 

.. code:: python
  
  s = was.rpc.lb (
    "@mysearch/rpc2", 
    use_cache = not refreshed and True or False
  ).getinfo ()
  result = s.dispatch (2, cache = 60, cache_if = (200, 201))


More About Cache Control: Model Synchronized Cache
```````````````````````````````````````````````````

*New in version 0.26.15*

`use_cache` value can be True, False or last updated time of base object. If last updated is greater than cached time, cache will be expired immediately and begin new query/request.

You can integrate your models changing and cache control.

First of all, you should set all cache control keys to Skitai for sharing model state beetween worker processes.

.. code:: python

  skitai.deflu ('tables.users', 'table.photos')

These Key names are might be related your database model names nor table names. Especially you bind Django model signal, these keys should be exaclty nodel class name. But in general cases, key names are fine if you easy to recognize.
  
These key names are not mutable and you cannot add new key after calling skitai.run ().
  
Then you can use setlu () and getlu (),

.. code:: python

  app = Atila (__name__)
  
  @app.route ("/update")
  def update (was):
    # update users tabale
    was.backend ('@mydb').execute (...)
    # update last update time by key string
    was.setlu ('tables.users')
  
  @app.route ("/query1")
  def query1 (was):
    # determine if use cache or not by last update information 'users'
    was.backend ('@mydb', use_cache = was.getlu ('tables.users')).execute (...)
  
  @app.route ("/query2")
  def query2 (was):
    # determine if use cache or not by last update information 'users'
    was.backend ('@mydb', use_cache = was.getlu ('tables.users')).execute (...)

It makes helping to reduce the needs for building or managing caches. And the values by setlu() are synchronized between Skitai workers by multiprocessing.Array.

If your query related with multiple models,

.. code:: python
  
  use_cache = was.getlu ("myapp.models.User", "myapp.models.Photo")

was.getlu () returns most recent update time stamp of given models.

*Available on Python 3.5+*

Also was.setlu () emits 'model-changed' events. You can handle event if you need. But this event system only available on Atila middle-ware.

.. code:: python
  
  app = Atila (__name__)
  
  @app.route ("/update")
  def update (was):
    # update users tabale
    was.backend ('@mydb').execute (...)
    # update last update time by key string
    was.setlu ('tables.users', something...)
  
  @app.on_broadcast ("model-changed:tables.users")
  def on_broadcast (was, *args, **kargs):
    # your code

Note: if @app.on_broadcast is located in mount function at services directory, even app.use_reloader is True, it is not applied to app when component file is changed. In this case you should manually reload app by resaving app file.


Working With Jinja2 Template
```````````````````````````````

*New in version 0.27*

Async request's benefit will be maximied at your view template rather than your controller. At controller, you just fire your requests and get responses at your template.

.. code:: python

  @app.route ("/")
  @app.login_required	
  def intro (was):
    was.g.aa = was.get ("https://example.com/blur/blur")
    was.g.bb = was.get ("https://example.com/blur/blur/more-blur")
    return was.render ('template.html')
	
Your template,

.. code:: html

  {% set response = was.g.aa.dispatch () %}  
  {% if response.status == 3 %}
    {{ was.response.throw ("500 Internal Server Error") }}
  {% endif %}
  
  {% if response.status_code == 200 %}
    {% for each in response.data %}
      ...
    {% endfor %}
  {% endif %}

*Available only with Atila*

Shorter version is for dispatch and throw HTTP error,

.. code:: html
  
  {% set response = was.g.aa.dispatch_or_throw ("500 Internal Server Error") %}


API Transaction ID
`````````````````````

*New in version 0.21*

For tracing REST API call, Skitai use global/local transaction IDs.

If a client call a API first, global transaction ID (gtxnid) is assigned automatically like 'GTID-C4676-R67' and local transaction ID (ltxnid) is '1000'.

You call was.get (), was.post () or etc, both IDs will be forwarded via HTTP request header. Most important thinng is that gtxnid is never changed by client call, but ltxnid will be changed per API call.

when client calls gateway API or HTML, ltxnid is 1000. And if it calls APIs internally, ltxnid will increase to 2001, 2002. If ltxnid 2001 API calls internal sub API, ltxnid will increase to 3002, and ltxnid 2002 to 3003. Briefly 1st digit is call depth and rest digits are sequence of API calls.

This IDs is logged to Skitai request log file like this. 

.. code:: bash

  2016.12.30 18:05:06 [info] 127.0.0.1:1778 127.0.0.1:5000 GET / \
  HTTP/1.1 200 0 32970 \
  GTID-C3-R8 1000 - - \
  "Mozilla/5.0 (Windows NT 6.1;) Gecko/20100101 Firefox/50.0" \
  4ms 3ms

Focus 3rd line above log message. Then you can trace a series of API calls from each Skitai instance's log files for finding some kind of problems.

In next chapters' features of 'was' are only available for *Atila WSGI container*. So if you have no plan to use Atila, just skip.


Inter-Processes State Sharing
-------------------------------------------

Skitai can run with multiple processes (a.k workers), It is possible matters synchronizing state between workers.

Like was.setlu () or getlu (), was provide setgs (), getgs ().

Most important thing is global state keys SHUOLD be defined before running skitai. And argument should be integer value.

.. code:: python

  skitai.defgs ("cluster.num-nodes", "region.somethig", ...)  
  ...
  
  skitai.run ()
  
Then you cna use these,

.. code:: python
  
  @app.route ("/nodes", method = ["POST", "DELETE"])
  def nodes (was, **nodinfos):
  	...
  	was.setgs ("cluster.num-nodes", was.getgs ("cluster.num-nodes") + 1, **nodeinfos)  	

As a result,

- cluster.num-nodes state value has been increased
- "cluster.num-nodes" and  \*\*nodeinfos are broadcated to mounted all *Atila* apps.

A app has interest for this,

.. code:: python

  @app.on_broadcast ("cluster.num-nodes")
  def num_nodes_changed (num_nodes, **nodeinfos):
    ...

But this broadcasting is just within current workers. 

All workers has interested in this event, You may add watching routine at app.maintain.

.. code:: python
  
  app.config.maintain_interval = 60
  app.store ["num_nodes"] = 0
  
  @app.maintain
  def maintain_num_nodes (was, now):
  	...
  	num_nodes = was.getgs ("cluster.num-nodes")
  	if app.store ["num_nodes"] != num_nodes:
  	  app.store ["num_nodes"] = num_nodes
  	  app.broadcast ("cluster:num_nodes")



Websocket Related Methods of 'was'
------------------------------------

For more detail, see Websocket section.

- was.wsinit () # wheather handshaking is in progress
- was.wsconfig (spec, timeout, message_type)
- was.wsopened ()
- was.wsclosed ()
- was.wsclient () # get websocket client ID


Utility Methods of 'was'
---------------------------

This chapter's 'was' services are also avaliable for all WSGI middelwares.

- was.status () # HTML formatted status information
- was.get_lock (name = "__main__") # getting process lock
- was.gentemp () # return temp file name with full path
- was.restart () # Restart Skitai App Engine Server, but this only works when processes is 1 else just applied to current worker process.
- was.shutdown () # Shutdown Skitai App Engine Server, but this only works when processes is 1 else just applied to current worker process.


HTML5 Websocket
====================

*New in version 0.11*

The HTML5 WebSockets specification defines an API that enables web pages to use the WebSockets protocol for two-way communication with a remote host.

Skitai can be HTML5 websocket server and any WSGI containers can use it.

But I'm not sure my implemetation is right way, so it is experimental and could be changable.

First of all, see conceptual client side java script for websocket using Vuejs.

.. code:: html

  <div id="app">
    <ul>
      <li v-for="log in logs" v-html="log.text"></li>
    </ul>
    <input type="Text" v-model="msg" @keyup.enter="push (msg); msg='';">
  </div>
  
  <script>  
  vapp = new Vue({
    el: "#app",
    data: {  
      ws_uri: "ws://www.yourserver.com/websocket",
      websocket: null,
      out_buffer: [],
      logs: [],
      msg = '',
    },
        
    methods: {
      
      push: function (msg) {
        if (!msg) {
          return
        }      
        this.out_buffer.push (msg)
        if (this.websocket == null) {
          this.connect ()
        } else {
          this.send ()
        }
      },
      
      handle_read: function (evt)  {
        this.log_info(evt.data)
      },
      
      log_info: function (msg) {    
        if (this.logs.length == 10000) {
          this.logs.shift ()
        }      
        this.logs.push ({text: msg})      
      },
      
      connect: function () {
        this.log_info ("connecting to " + this.ws_uri)
        this.websocket = new WebSocket(this.ws_uri)      
        this.websocket.onopen = this.handle_connect
        this.websocket.onmessage = this.handle_read
        this.websocket.onclose = this.handle_close
        this.websocket.onerror = this.handle_error
      },
      
      send: function () {      
        for (var i = 0; i < this.out_buffer.length; i++ ) {
          this.handle_write (this.out_buffer.shift ())
        }
      },
      
      handle_write: function (msg) {
        this.log_info ("SEND: " + msg)
        this.websocket.send (msg)
      },
      
      handle_connect: function () {
        this.log_info ("connected")
        this.send ()
      },
      
      handle_close: function (evt)  {
        this.websocket.close()
        this.websocket = null
        this.log_info("DISCONNECTED")
      },
      
      handle_error: function (evt)  {
        this.log_info('ERROR: ' + evt.data)
      },
      
    },
    
    mounted: function () {      
      this.push ('Hello!')
    },
    
  })
  
  </script>


If your WSGI app enable handle websocket, it should give  initial parameters to Skitai like this,

.. code:: python
  
  def websocket (was, message):
    if was.wshasevent ():
      if was.wsinit ():
        return was.wsconfig (
          websocket design specs, 
          keep_alive_timeout = 60, 
          message_encoding = None
        )    

*websocket design specs* can  be choosen one of 4.

WS_SIMPLE

  - Thread pool manages n websocket connection
  - It's simple request and response way like AJAX  
  - Low cost on threads resources, but reposne cost is relatvley high than the others

WS_THREADSAFE (New in version 0.26)

  - Mostly same as WS_SIMPLE
  - Message sending is thread safe
  - Most case you needn't this option, but you create uourself one or more threads using websocket.send () method you need this for your convinience
 
WS_GROUPCHAT (New in version 0.24)
  
  - Thread pool manages n websockets connection
  - Chat room model

*keep alive timeout* is seconds.

*message_encoding*

Websocket messages will be automatically converted to theses objects. Note that option is only available with Atila WSGI container.

  - WS_MSG_JSON
  - WS_MSG_XMLRPC


WWW-Authenticate
-----------------

Some browsers do not support WWW-Authenticate on websocket like Safari, then Skitai currently disables WWW-Authenticate for websocket, so you should be careful for requiring secured messages.

General Usages
---------------

Handling websocket has 2 parts - event handling and message handling.

Websocket Events
``````````````````

Currently websocket has 3 envets.

- skitai.WS_EVT_INIT: in handsahking progress
- skitai.WS_EVT_OPEN: just after websocket configured
- skitai.WS_EVT_CLOSE: client websocket channel disconnected

When event occured, message is null string, so WS_EVT_CLOSE is not need handle, but WS_EVT_OPEN would be handled - normally just return None value.

At Flask, use like this.

.. code:: python
  
  event = request.environ.get ('websocket.event')
  if event:
    if event == skitai.WS_EVT_INIT:
      return request.environ ['websocket.config'] = (...)
    elif event == skitai.WS_EVT_OPEN:
      return ''
    elif event == skitai.WS_EVT_CLOSE:
      return ''
    elif event:
      return '' # should return null string
      
At Atila, handling events is more simpler,

.. code:: python
  
  if was.wshasevent ():
    if was.wsinit ():
      return was.wsconfig (spec, timeout, message_type)    
    elif was.wsopened ():
      return
    elif was.wsclosed ():
      return  
    return
        
And from version 0.26.18, much more simpler and elegant style is available.

See *More About Websocket* Section.
 

Handling Message
``````````````````

Message is received by first arg (at below exapmle, message arg), and you response for this by returning value.

.. code:: python

  @app.route ("/websocket/echo")
  def echo (was, message):
    return "ECHO:" + message
    

Full Example
``````````````

Websocket method MUST have both of event and message handling parts.

Let's see full example, client can connect by ws://localhost:5000/websocket/echo.

.. code:: python

  from atila import Atila
  import skitai
  
  app = Atila (__name__)
  app.debug = True
  app.use_reloader = True

  @app.route ("/websocket/echo")
  def echo (was, message):
    #-- event handling
    if was.wshasevent ():
      if was.wsinit ():
        return was.wsconfig (skitai.WS_SIMPLE, 60)
      elif was.wsopened ():
        return "Welcome Client %s" % was.wsclient ()
      return      
    #-- message handling  
    
    return "ECHO:" + message

For getting another args, just add args behind message arg.

.. code:: python
  
  num_sent = {}  
  
  @app.route ("/websocket/echo")
  def echo (was, message, clinent_name):
    global num_sent    
    client_id = was.wsclient ()
    
    if was.wshasevent ():
      if was.wsinit ():
        num_sent [client_id] = 0      
        return was.wsconfig (skitai.WS_SIMPLE, 60)
      elif was.wsopened ():
        return
      elif was.wsclosed ():      
        del num_sent [client_id]
        return
      return
        
    num_sent [client_id] += 1
    return "%s said:" % (clinent_name, message)

Now client can connect by ws://localhost:5000/websocket/chat?client_name=stevemartine.
    
Once websocket configured by was.wsconfig (), whenever message is arrived from this websocket connection, called this *echo* method. And you can use all was services as same as other WSGI methods.

was.wsclient () is equivalent to was.env.get ('websocket.client') and has numeric unique client id.


For Flask Users
``````````````````

At Flask, Skitai can't know which variable name receive websocket message, then should specify.

.. code:: python

  from flask import Flask, request 
  import skitai
  
  app = Flask (__name__)
  app.debug = True
  app.use_reloader = True

  @app.route ("/websocket/echo")
  def echo ():
    event = request.environ.get ('websocket.event')
    client_id = request.environ.get ('websocket.client')
    
    if event == skitai.WS_EVT_INIT:
      request.environ ["websocket.config"] = (skitai.WS_SIMPLE, 60, ("message",))
      return ""
    elif event == skitai.WS_EVT_OPEN:
      return "Welcome %d" % client_id
    elif event:
      return ""  
    return "ECHO:" + request.args.get ("message")

In this case, variable name is ("message",), It means take websocket's message as "message" arg.

If returned object is python str type, websocket will send messages as text tpye, if bytes type, as binary. But Flask's return object is assumed as text type. 

Also note, at flask, you should not return None, so you should return null string, if you do not want to send any message.


Send Messages Through Websocket Directly
``````````````````````````````````````````

It needn't return message, but you can send directly multiple messages through was.websocket,

.. code:: python

  @app.route ("/websocket/echo")
  def echo (was, message):
    if was.wsinit ():
      return was.wsconfig (skitai.WS_SIMPLE, 60)
    elif was.wshasevent (): # ignore all events
      return
      
    was.websocket.send ("You said," + message)  
    was.websocket.send ("I said acknowledge")

This way is very useful for Flask users, because Flask's return object is bytes, so Skitai try to decode with utf-8 and send message as text type. If Flask users want to send binary data, just send bytes type.

.. code:: python

  @app.route ("/websocket/echo")
  def echo ():
    event = request.environ.get ('websocket.event')
    if event == skitai.WS_EVT_INIT:
      request.environ ["websocket.config"] = (skitai.WS_SIMPLE, 60, ("message",))
      retrurn ''
    elif event:
      return ''   
      
    request.environ ["websocket"].send (
      ("You said, %s" % message).encode ('iso8859-1')
    )


Use Message Encoding
`````````````````````

For your convinient, message automatically load and dump object like JSON. But this feature is only available with Atila.

.. code:: python

  @app.route ("/websocket/json")
  def json (was, message):
    if was.wsinit ():
      return was.wsconfig (skitai.WS_SIMPLE, 60, skitai.WS_MSG_JSON)
    elif was.wshasevent ():
      return
            
    return dbsearch (message ['query'], message ['offset'])

JSON message is automatically loaded to Python object, and returning object also will dump to JSON.

Currently you can use WS_MSG_JSON and WS_MSG_XMLRPC. And I guess streaming and multi-chatable gRPC over websocket also possible, I am testing it.


Simple Data Request & Response
-------------------------------

Here's a echo app for showing simple request-respone.

Client can connect by ws://localhost:5000/websocket/chat.

.. code:: python

  @app.route ("/websocket/echo")
  def echo (was, message):
    if was.wsinit ():
      return was.wsconfig (skitai.WS_SIMPLE, 60)
    elif was.wshasevent ():
      return
            
    return "ECHO:" + message

First args (message) are essential. Although you need other args, you must position after this essential arg.


Thread Safe Websocket
-----------------------

Here's a websocket app example creating sub thread(s),

.. code:: python
  
  class myProgram:
    def __init__ (self, websocket):
      self.websocket = websocket
      self.__active = 0
      self.__lock = trheading.Lock ()
    
    def run (self):
      while 1:
        with self.lock:
          active = self.__active
        if not active: break           
        self.websocket.send ('Keep running...')
        time.sleep (1)
      self.websocket.send ('Terminated')
          
    def handle_command (self, cmd):
      if cmd == "start":        
        with self.lock:
          self.__active = 1
        threading.Thread (self.run).start ()
                
      elif cmd == "stop":
        with self.lock:
          self.__active = 0
        self.websocket.send ('Try to stop...')
      
      else:
        self.websocket.send ('I cannot understand your command')
  
  app = Atila (__name__)
  
  @app.before_mount
  def before_mount (wac):  
    wac.register ('wspool', {})
    
  @app.route ("/websocket/run")
  def run (was, message):
    if was.wshasevent ():
      if was.wsinit ():    
        was.wsconfig (skitai.WS_THREADSAFE, 7200)        
      elif was.wsopened ():
        was.wspool [id (was.websocket)] = myProgram (was.websocket)        
      elif was.wsclosed ():
        ukey = id (was.websocket)
        if ukey in was.wspool:
          was.wspool [ukey].kill ()
          del was.wspool [ukey]          
      return
    
    runner = was.hounds [id (was.websocket)]
    runner.handle_command (m)


Group Chat Websocket
---------------------

This is just extension of Simple Data Request & Response. Here's simple multi-users chatting app.

This feature will NOT work on multi-processes run mode.

Many clients can connect by ws://localhost:5000/websocket/chat?roomid=1. and can chat between all clients.

.. code:: python

  @app.route ("/chat")
  def chat (was, message, room_id):   
    client_id = was.wsclient ()
    if was.wshasevent ():
      if was.wsinit ():
        return was.wsconfig (skitai.WS_GROUPCHAT, 60)    
      elif was.wsopened ():
        return "Client %s has entered" % client_id
      elif was.wsclosed ():
        return "Client %s has leaved" % client_id
      return
      
    return "Client %s Said: %s" % (client_id, message)

In this case, first 2 args (message, room_id) are essential.

For sending message to specific client_id,

.. code:: python
  
  clients = list (was.websocket.clients.keys ())
  was.websocket.send ('Hi', clients [0])
  # OR
  return 'Hi', clients [0]


At Flask, should setup for variable names you want to use,

.. code:: python
  
  if request.environ.get ("websocket.event") == skitai.WS_EVT_INIT:
    request.environ ["websocket.config"] = (
      skitai.WS_GROUPCHAT, 
      60, 
      ("message", "room_id")
    )
    return ""


Project Purpose
===================

Skitai App Engine's original purpose is to serve python fulltext search engine Wissen_ which is my another pypi work. And I found that it is possibly useful for building and serving websites.

Anyway, I am modifying my codes to optimizing for enabling service on Linux machine with relatvely poor H/W (ex. AWS_ t2.nano instance) and making easy to auto-scaling provided cloud computing service like AWS_.

If you need lots of outside http(s) resources connecting jobs and use PostgreSQL, it might be worth testing and participating this project.

Also note it might be more efficient that circumstance using `Gevent WSGI Server`_ + Flask. They have well documentation and already tested by lots of users.


.. _Wissen: https://pypi.python.org/pypi/wissen
.. _AWS: https://aws.amazon.com
.. _`Gevent WSGI Server`: http://www.gevent.org/


Links
======

- `GitLab Repository`_
- Bug Report: `GitLab issues`_

.. _`GitLab Repository`: https://gitlab.com/hansroh/skitai
.. _`GitLab issues`: https://gitlab.com/hansroh/skitai/issues
.. _`Skitai WSGI App Engine Daemon`: https://pypi.python.org/pypi/skitaid


Change Log
===========

- 0.28 (Feb 2019)
	
  - getwait () and getswait () are integrated into dispatch ()
  - add data_or_throw () and one_or_throw ()  	
  - was.promise has been deprecated, use was.futures: see Atila documentation
  - reinstate gc.collect () schedule
  - fix GTXID
  - fix app reloader
  - remove gc.collect () schedule
  - support SQLAlchemy query statement object 
  - removed sugar methods: was.getjson, getxml, postjson, ..., instead use headers parameter or app.config.default_request_type 
  - skitai.win32service has been moved to rs4.psutil.win32service
  - improve 'was' magic method search speed
  - seperate skitai.saddle into atila

- 0.27.6 (Jan 2019)

  - rename directory decorative to services
  - change from skital.saddle.contrib.decorative to skital.saddle.contrib.services
    
- 0.27.3 (May 2018)
  
  - remove -v option from skitai and smtpda
  - add script: skitai
  - remove scripts: skitai-smtpda and skitai-cron
  - remove skitai.enable_smtpda (), skitai.cron ()
  
- 0.27.2 (May 2018)

  - add was.request.get_real_ip () and was.request.is_private_ip ()
  - fix CORS preflight
  
- 0.27.1 (May 2018)
  
  - sqlphile bug fixed and change requirements  
  
- 0.27 (Apr 2018)
  
  - add app.setup_sqlphile ()
  - add @app.mounted_or_reloaded decorator
  - removed @app.auth_required, added @app.authorization_required (auth_type)
  - rename @app.preworks -> @app.run_before and @app.postworks ->  @app.run_after
  - add @app.bearer_handler
  - add was.mkjwt and was.dejwt
  - add was.timestamp amd was.uniqid
  - renamed was.token -> was.mktoken
  - renamed api -> API, for_api -> Fault
  - skitai.use_django_models has been deprecated, use skitai.alias
  - functions are integrated skitai.mount_django into skitai.mount, skitai.alias_django into skitai.alias
  - fix empty payload posting
  - add was.partial and was.basepath
  - raise NameError when non-exists funtion name to was.ap
  - fix default arg is missing on was.ab
  - add skitai.launch and saddle.make_client for unittest

0.26 (May 2017)
  
- 0.26.18 (Jan 2018)
    
  - fix HTTP2 trailers
  - fix HTTP2 flow control window
  - remove was.response.traceback(), use was.response.for_ap (traceback = True)
  - rename was.sqlmap to was.sql
  - add @app.auth_required and  @app.auth_not_required decorator
  - change default export script to __export__.py
  - remove app reloading progress:
   
    - before:
     
      - before_umount (was)
      - umounted (wac)      
      - before_remount (wac): deprecated
      - remounted (was): deprecated
      
    - now:
    
      - before_reload (was)
      - reloaded (was)
    
  - change app.model_signal () to app.redirect_signal (), add @app.on_signal ()
  - change skitai.addlu to skitai.deflu (args, ...)
  - add @app.if_file_modified
  - add @app.preworks and @app.postworks
  - fix HTTP/2 remote flow control window
  - fix app.before_mount decorator exxcute point
  - add was.gentemp () for generating temp file name
  - add was.response.throw (), was.response.for_api() and was.response.traceback()
  - add @app.websocket_config (spec, timeout, onopen_func, onclose_func, encoding)
  - was.request.get_remote_addr considers X-Forwarded-For header value if exists
  - add param keep param to was.csrf_verify() 
  - add and changed app life cycle decorators:
    
    - before_mount (wac)
    - mounted (was) 
    - before_remount (wac)
    - remounted (was)
    - before_umount (was)
    - umounted (wac)
    
  - add skitai.saddle.contrib.django,auth for integrating Django authorization
  - change was.token(),was.detoken(), was.rmtoken() 
  - add jsonrpc executor  
  - add some methods to was.djnago: login (), logout (), authenticate () and update_session_auth_hash () 
  - add app.testpass_required decorator  
  - add decorative concept

- 0.26.17 (Dec 2017)
  
  - can run SMTP Delivery Agent and Task Scheduler with config file
  - add error_handler (prev errorhandler) decorator
  - add default_error_handler (prev defaulterrorhandler) decorator
  - add login_handler, login_required decorator
  - add permission_handler, permission_required decorator
  - add app events emitting
  - add was.csrf_token_input, was.csrf_token and was.csrf_verify()    
  - make session iterable  
  - prevent changing function spec by decorator
  - change params of use_django_models: (settings_path, alias), skitai.mount_django (point, wsgi_path, pref = pref (True), dbalias = None, host = "default")
  
- 0.26.16 (Oct 2017)

  - add app.sqlmaps
  - add use_django_models (settings_path), skitai.mount_django (point, wsgi_path, pref = pref (True), host = "default")
  - fix mbox, add app.max_client_body_size
  - add skitai.addlu (args, ...)
  - fix promise and proxing was objects
  - change method name from skitai.set_network_timeout to set_erquest_timeout
  - fix getwait, getswait. get timeout mis-working
  - fix backend_keep_alive default value from 10 to 1200
  - fix dbi reraise on error
  - JSON as arguments
  
- 0.26.15
  
  - added request.form () and request.dict ()
  - support Django auto reload by restarting workers
  - change DNS query default protocol from TCP to UDP (posix only)
  - add skitai.set_proxy_keep_alive (channel = 60, tunnel = 600) and change default proxy keep alive to same values
  - increase https tunnel keep alive timeout to 600 sec.
  - fix broad event bus
  - add getjson, deletejson, this request automatically add header 'Accept: application/json'
  - change default request content-type from json to form data, if you post/put json data, you should change postjson/putjson
  - add skitai.trackers (args,...) that is equivalant to skitai.lukeys ([args])
  - fix mounting module
  - app.storage had been remove officially, I cannot find any usage. but unoficially it will be remains by some day
  - add skitai.lukeys () and fix inconsistency of was.setlu & was.getlu between multi workers
  - was.storage had been remove
  - add skitai.set_worker_critical_point ()
  - fix result object caching
  - add app.model_signal (), was.setlu () and was.getlu ()
  
- 0.26.14
  
  - add app.storage and was.storage
  - removed wac._backend and wac._upstream, use @app.mounted and @app.umount
  - replaced app.listen by app.on_broadcast
  
- 0.26.13
  
  - add skitai.log_off (path,...)
  - add reply content-type to request log, and change log format
  - change posix process display name
  
- 0.26.12
  
  - change event decorator: @app.listen -> @app.on_broadcast
  - adaptation to h2 3.0.1
  - fix http2 flow controling    
  - fix errorhandler and add defaulterrorhandler
  - fix WSGI response handler
  - fix cross app URL building
  - Django can be mounted
  - fix smtpda & default var directory
  - optimize HTTP/2 response data
  - fix HTTP/2 logging when empty response body
  - http_response.outgoing is replaced by deque
  - change default mime-type from text/plain to application/octet-stream in response header
  - HTTP response optimized
  
- 0.26.10
  
  - start making pytest scripts
  - add was-wide broadcast event bus: @app.listen (event), was.broadcast (event, args...) and @was.broadcast_after (event)
  - add app-wide event bus: @app.on (event), was.emit (event, args...) and @was.emit_after (event)
  - remove @app.listento (event) and was.emit (event, args...)
  
- 0.26.9
  
  - add event bus: @app.listento (event) and was.emit (event, args...)
  
- 0.26.8
  
  - fix websocket GROUPCHAT
  - add was.apps
  - was.ab works between apps are mounted seperatly
 
- 0.26.7 
  
  - add custom error template on Saddle
  - add win32 service tools
  - change class method name from make_request () to backend ()
  - retry once if database is disconnected by keep-live timeout
  - drop wac.make_dbo () and wac.make_stub ()
  
- 0.26.6
  
  - add wac.make_dbo (), wac.make_stub () and wac.make_request ()
  - wac.ajob () has been removed
  - change repr name from wasc to wac
  - websocket design spec, WEBSOCKET_DEDICATE_THREADSAFE has been removed and WEBSOCKET_THREADSAFE is added
  - fix websocket, http2, https proxy tunnel timeout, related set_network_timeout () is recently added
  
- 0.26.4.1: add set_network_timeout (timoutout = 30) and change default keep alive timeout from 2 to 30
- 0.26.4: fix incomplete sending when resuested with connection: close header
- 0.26.3.7: enforce response to HTTP version 1.1 for 1.0 CONNECT with 1.0 request
- 0.26.3.5: revert multiworkers
- 0.26.3.2: fix multiworkers
- 0.26.3.1: update making for self-signing certification
- 0.26.3: add skitai.enable_forward
- 0.26.2.1: remove was.promise.render_all (), change method name from was.promise.push () to send ()
- 0.26.2: change name from was.aresponse to was.promise
- 0.26.1.1: add skitai.abspath (\*args)
- 0.26.1: fix proxy & proxypass, add was.request.scheme and update examples
- change development status to Beta
- fix Saddlery routing
- disable WWW-Authenticate on websocket protocol
- support CORS (Cross Origin Resource Sharing)
- support PATCH method
- runtime app preferences and add __init__.bootstrap (preference)
- fix route caching
- auto reload sub modules in package directory, if app.use_reloader = True
- new was.request.json ()
- integrated with skitaid package, single app file can contain all configure options
- level down developement status to alpha
- fix sqlite3 closing

0.25 (Feb 2017)

- 0.25.7: fix fancy url, non content-type header post/put request
- 0.25.6: add Chameleon_ template engine
- 0.25.5: app.jinja_overlay ()'s default args become jinja2 default
- 0.25.4.8: fix proxy retrying
- 0.25.4 license changed from BSD to MIT, fix websocket init at single thread
- 0.25.3 handler of promise args spec changed, class name is cahnged from AsyncResponse to Promise
- 0.25.2 fix promise exception handling, promise can send streaming chunk data
- 0.25.1 change app.jinja_overlay () default values and number of args, remove raw line statement
- project name chnaged: Skitai Library => Skitai App Engine

0.24 (Jan 2017)

- 0.24.9 bearer token handler spec changed
- 0.24.8 add async response, fix await_fifo bug
- 0.24.7 fix websocket shutdown
- 0.24.5 eliminate client arg from websocket config
- 0.24.5 eliminate event arg from websocket config
- fix proxy tunnel
- fix websocket cleanup
- change websocket initializing, not lower version compatible
- WEBSOCKET_MULTICAST deprecated, and new WEBSOCKET_GROUPCHAT does not create new thread any more

0.23 (Jan 2017)

- ready_producer_fifo only activated when proxy or reverse proxy is enabled, default deque will be used
- encoding argument was eliminated from REST call 
- changed RPC, DBO request spec
- added gRPC as server and client
- support static files with http2
- fix POST method on reverse proxying

0.22 (Jan 2017)

- 0.22.7 fix was.upload(), was.post*()
- 0.22.5 fix xml-rpc service
- 0.22.4 fix proxy
- 0.22.3
  
  - fix https REST, XML-RPC call
  - fix DB pool

- 0.22 
  
  - Skitai REST/RPC call now uses HTTP2 if possible
  - Fix HTTP2 opening with POST method
  - Add logging on disconnecting of Websocket, HTTP2, Proxy Tunnel channels
  
  - See News
  
0.21 (Dec 2016)

- 0.21.17 - fix JWT base64 padding problem
- 0.21.8 - connected with MongoDB asynchronously
- 0.21.3 - add JWT (JSON Web Token) handler, see `Skitai WSGI App Engine Daemon`_
- 0.21.2 - applied global/local-transaction-ID to app logging: was.log (msg, logtype), was.traceback ()
- 0.21 - change request log format, add global/local-transaction-ID to log file for backtrace

0.20 (Dec 2016)

- 0.20.15 - minor optimize asynconnect, I wish
- 0.20.14 - fix Redis connector's threading related error
- 0.20.4 - add Redis connector
- 0.20 - add API Gateway access handler

0.19 (Dec 2016)

- Reengineering was.request methods, fix disk caching  

0.18 (Dec 2016)

- 0.18.11 - default content-type of was.post(), was.put() has been changed from 'application/x-www-form-urlencoded' to 'application/json'. if you use this method currently, you SHOULD change method name to was.postform()

- 0.18.7 - response contents caching has been applied to all was.request services (except websocket requests).

0.17 (Oct 2016)

- `Skitai WSGI App Engine Daemon`_ is seperated

0.16 (Sep 2016)

- 0.16.20 fix SSL proxy and divide into package for proxy & websocket_handler
- 0.16.19 fix HTTP2 cookie
- 0.16.18 fix handle large request body
- 0.16.13 fix thread locking for h2.Connection
- 0.16.11 fix pushing promise and response on Firefox
- 0.16.8 fix pushing promise and response
- 0.16.6 add several configs to was.app.config for limiting post body size from client
- 0.16.5 add method: was.response.hint_promise (uri) for sending HTP/2 PUSH PROMISE frame
- 0.16.3 fix flow control window
- 0.16.2 fix HTTP/2 Uprading for "http" URIs (RFC 7540 Section 3.2)
- 0.16 HTTP/2.0 implemented with hyper-h2_

0.15 (Mar 2016)

- fixed fancy URL <path> routing
- add Websocket design spec: WEBSOCKET_DEDICATE_THREADSAFE
- fixed Websocket keep-alive timeout
- fixed fancy URL routing
- 'was.cookie.set()' method prototype has been changed.
- added Named Session & Messaging Box
- fix select error when closed socket, thanks to spam-proxy-bots
- add mimetypes for .css .js
- fix debug output
- fix asynconnect.maintern
- fix loosing end of compressed content
- fix app reloading, @shutdown
- fix XMLRPC response and POST length
- add was.mbox.search (), change spec was.mbox.get ()
- fix routing bugs & was.ab()
- add saddle.Saddlery class for app packaging
- @app.startup, @app.onreload, @app.shutdown arguments has been changed

0.14 (Feb 2016)

- fix proxy occupies CPU on POST method failing
- was.log(), was.traceback() added
- fix valid time in message box 
- changed @failed_request arguments and can return custom error page
- changed skitaid.py command line options, see 'skitaid.py --help'
- batch task scheduler added
- e-mail sending fixed
- was.session.getv () added
- was.response spec. changed
- SQLite3 DB connection added

0.13 (Feb 2016)

- was.mbox, was.g, was.redirect, was.render added  
- SQLite3 DB connection added

0.12 (Jan 2016) - Re-engineering 'was' networking, PostgreSQL & proxy modules

0.11 (Jan 2016) - Websocket implemeted

0.10 (Dec 2015) - WSGI support
  
.. _Chameleon: https://chameleon.readthedocs.io/en/latest/index.html
