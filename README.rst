===================
Skitai App Engine
===================

At a Glance
=============

Here's a simple equation:

.. code:: bash

  Skitai = Nginx + uWSGI + Flask + Aquests
  
And simple to run:

.. code:: bash

  pip3 install skitai
  python3 app.py -d

Your app will work for your thousands or miliions of customers.

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

Conceptually, Skitai has been seperated into two components:

1. Skitai App Engine Server, for WSGI apps
2. Skito-Saddle, the small WSGI container integrated with Skitai. But you can also mount any WSGI apps and frameworks like Flask (I cannot sure).

Skitai is not a just developing server like some frameworks provides. It is supporsed to work fine under real service situation by alone. And it makes your app take off to the world, just by appending a few lines on your app.

.. _hyper-h2: https://pypi.python.org/pypi/h2
.. _Zope: http://www.zope.org/
.. _Flask: http://flask.pocoo.org/
.. _PostgreSQL: http://www.postgresql.org/
.. __: http://www.nightmare.com/medusa/medusa.html


.. contents:: Table of Contents


Installation
=========================

**Requirements**

Python 3.4+  

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
    pref, 
    path = "./mydjango"
  )

  # or for your convinience,  
  skitai.mount_django ("/", "mydjango/mydjango/wsgi.py", pref)  
 
Note that if app is smae location with django manage.py, you need not path param.

Also note that if you set pref.use_reloader = True, it is possible to replace Django development server (manage,py runserver), But it will work on posix only, because Skitai reloads Django app by restart worker process, Win32 version doesn't support.


Logging and Console Displaying For Developing/Debugging
----------------------------------------------------------

If you do not specify log file path, all logs will be displayed in console, bu specifed all logs will be written into file.

.. code:: python
  
  skitai.mount ('/', app)
  skitai.run (
    address = "0.0.0.0",
    port = 5000,    
    logpath = '/var/logs/skitai'
  )

If you also want to view logs through console for spot developing, you run app.py with-v option.

.. code:: bash

  python3 app.py -v


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

This features is limited by your WSGI container. If you use Skito-Saddle container, you can run with single threading mode by using Skito-Saddle's async streaming response method. But you don't and if you have plan to use Skitai 'was' requests services, you can't single threading mode and you SHOULD run with multi-threading mode.

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


  # OR Skito-Saddle App  
  from skitai.saddle import Saddle  
  app = Saddle (__name__)
  
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

  app = Saddle (__name__)
    
  @app.route('/')
  def index (was):   
    return "Hello World Ver.1"

And in same directory 2nd version of app file is app_v2.py.

.. code:: python  

  app = Saddle (__name__)
      
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
 

Microservices
```````````````````

*Saddlery deprecated in version 0.26.11*

Skitai recommend your big service into seperated micro-apps.

app.py is starter script by importing skitai and mounting multiple apps.

.. code:: python
  
  import skitai    
  
  pref = skitai.pref ()
  pref.use_reloader = True
  
  skitai.mount ('/', 'static')
  skitai.mount ('/', 'index.py', 'app', pref)
  skitai.mount ('/admin', 'admin.py', 'app', pref)
  skitai.mount ('/trade', 'trade.py', 'app', pref)  
  skitai.run ()  

And your pysical directory structure including app.py is,

.. code:: bash

  templates/layout/*.html # for shared layout templates
  templates/*.html
  
  decorative/*.py # app library, all modules in this directory will be watched for reloading
  
  static/images # static files
  static/js
  static/css
  
  app.py # this is starter script
  index.py
  trade.py  
  admin.py
  
This structure make highly focus on each microservices and make easy to move or apply scaling by serivce traffic increment.

For communicating between apps using events, URL building and accessing another app, please refer previous chapters.
 

Mounting With Virtual Host
-------------------------------

.. code:: python
  
  if __name__ == "__main__": 
  
    import skitai
    skitai.mount ('/', 'site1.py', host = 'www.site1.com')
    skitai.mount ('/', 'site2.py', host = 'www.site2.com')
    skitai.run ()


Runtime App Preference
-------------------------

**New in version 0.26**

Usally, your app preference setting is like this:

.. code:: python

  app = Saddle(__name__)
  
  app.use_reloader = True
  app.debug = True
  app.config ["prefA"] = 1
  app.config ["prefB"] = 2
  
Skitai provide runtime preference setting.

.. code:: python
  
  import skitai
  
  pref = skitai.pref ()
  pref.use_reloader = 1
  pref.debug = 1
  
  pref.config ["prefA"] = 1
  pref.config.prefB = 2
  
  skitai.mount ("/v1", "app_v1/app.py", "app", pref)
  skitai.run ()
  
Above pref's all properties will be overriden on your app.

Runtime preference can be used with skitai initializing or complicated initializing process for your app.

You can create __init__.py at same directory with app. And bootstrap () function is needed.

__init__.py

.. code:: python
  
  import skitai
  from . import cronjob
  
  def bootstrap (pref):
    if pref.config.get ('enable_cron')
      skitai.cron ('*/10 * * * *', "%s >> /var/log/sitai/cron.log" % cronjob.__file__)
      skitai.mount ('/cron-log', '/var/log/sitai')
            
    with open (pref.config.urlfile, "r") as f:
      pref.config.urllist = [] 
      while 1:
        line = f.readline ().strip ()
        if not line: break
        pref.config.urllist.append (line.split ("  ", 4))

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

  from skitai.saddle import Saddle
  from skitai.win32service import ServiceFramework
  
  class ServiceConfig (ServiceFramework):
    _svc_name_ = "SAE_EXAMPLE"
    _svc_display_name_ = "Skitai Example Service"
    _svc_app_ = __file__
    _svc_python_ = r"c:\python34\python.exe"
  
  app = Saddle (__name__)
  
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
In case Flask, it seems 'url_for' generate url by joining with env["SCRIPT_NAME"] and route point, so it's not problem. Skito-Saddle can handle obiously. But I don't know other WSGI containers will work properly.

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

.. code:: python
  
  skitai.enable_smtpda (
    '127.0.0.1:25', 'user', 'password', 
    ssl = False, max_retry = 10, keep_days = 3
  )
  skitai.mount ('/', app)
  skitai.run ()

All e-mails are saved into *varpath* and varpath is not specified default is /var/temp/skitai

Batch Task Scheduler
````````````````````````

*New in version 0.26*

Sometimes app need batch tasks for minimum response time to clients. At this situateion, you can use taks scheduling tool of OS - cron, taks scheduler - or can use Skitai's batch task scheduling service for consistent app management.

.. code:: python
  
  skitai.cron ("*/2 */2 * * *", "/home/apps/monitor.py  > /home/apps/monitor.log 2>&1")
  skitai.cron ("9 2/12 * * *", "/home/apps/remove_pended_files.py > /dev/null 2>&1")
  skitai.mount ('/', app)  
  skitai.run ()

Taks configuarion is very same with posix crontab.

Note that these tasks run only with Skitai, If Skitai is stopped, tasks will also stopped.


Run With Config File
````````````````````````
*New in version 0.26.17*

Both of SMTP and Taks Scheduler can be run with config file, it may be particulary useful in case you run multiple skitai instances.

.. code:: bash
  
  # ~/.skitai.conf
  
  [common]
  log-path =

  [smtpda]
  verbose = false
  max-retry = 10
  keep-days = 1
  smtp-server = [your SMTP server]
  user = [your SMTP user name if you need]
  password = [your SMTP user password if you need]
  ssl = true

  [cron]
  verbose = false
  process-display-name = skitai-cron

  [:crontab]

And run scripts mannually,
  
.. code:: bash

  python3 -m skitai.bin.smtpda -f ~/hrroh/.skitai.conf
  python3 -m skitai.bin.cron -f ~/hrroh/.skitai.conf
  
.. code:: bash

  Options:
  
    -f or --config=[config path]
    -d or start: start as daemon
    restart
    stop
    status
  
  Example:
  
    python3 -m skitai.bin.smtpda -f ~/hrroh/.skitai.conf status
    python3 -m skitai.bin.smtpda -f ~/hrroh/.skitai.conf restart  
  
I you give cammnad line options, theses have more priority than config file.

And for running automatically on system boot, you can add this line to /etc/rc.local like this,

.. code:: bash

  # /etc/rc.local
  
  su - ubuntu -c "python -m skitai.server.bin.smtpda -f ~/.skitai.conf -d"

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
  skitai.cron ("*/2 */2 * * *", "%s > /home/apps/monitor.log 2>&1" % monitor)

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


Skitai with Nginx / Squid
---------------------------

Here's some helpful sample works for virtual hosting using Nginx / Squid.

For Nginx:

.. code:: python
    
  proxy_http_version 1.1;
  proxy_set_header Connection "";
  
  upstream backend {
    server 127.0.0.1:5000;
    keepalive 100;
  }
  
  server {
    listen 80;
    server_name www.oh-my-jeans.com;
    
    location / {    
      proxy_pass http://backend;
      proxy_set_header Host $host;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      add_header X-Backend "skitai app engine";
    }
    
    location /assets/ {
      alias /home/ubuntu/www/statics/assets/;    
    }
  }

Example Squid config file (squid.conf) is like this:

.. code:: python
    
    http_port 80 accel defaultsite=www.oh-my-jeans.com
    
    cache_peer 127.0.0.1 parent 5000 0 no-query originserver name=jeans    
    acl jeans-domain dstdomain www.oh-my-jeans.com
    http_access allow jeans-domain
    cache_peer_access jeans allow jeans-domain
    cache_peer_access jeans deny all 

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

Your app should be located at unsub/export/skitai/app.py

Then users uses your module can mount on skitai by like this,

.. code:: python
  
  import unsub
  
  pref = skitai.pref ()  
  pref.config.urlfile = skitai.abspath ('resources', 'urllist.txt')
  
  skitai.mount ("/v1", unsub, "app", pref)
  skitai.run ()
  
If your app filename is not app.py but app_v1.py for version management,

.. code:: python
  
  skitai.mount ("/v1", (unsub, "app_v1.py"), "app", pref)
  

If your app need bootstraping or capsulizing complicated initialize process from simple user settings, write code to unsub/export/skitai/__init__.py.

.. code:: python
  
  import skitai
  
  def bootstrap (pref):    
    if pref.config.get ('enable_cron'):
      from . import cronjob
      skitai.cron ('*/10 * * * *', cronjob.__file__)
            
    with open (pref.config.urlfile, "r") as f:
      urllist = [] 
      while 1:
        line = f.readline ().strip ()
        if not line: break
        urllist.append (line.split ("  ", 4))
      pref.config.urllist = urllist  
     
 
Example
----------

`Wissen RESTful API`_ is an WSGI implementation for Wissen_ with Skitai App Engine.

.. _`Wissen RESTful API`: https://gitlab.com/hansroh/wissen/blob/master/wissen/export/skitai/
    


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

But Saddle WSGI container integrated with Skitai, use just like Python 'self'.

It will be easy to understand think like that:

- Skitai is Python class instance
- 'was' is 'self' which first argument of instance method
- Your app functions are methods of Skitai instance

.. code:: python
  
  @app.route ("/")
  def hello (was, name = "Hans Roh"):
    was.get ("http://...")
    ...

Simply just remember, if you use WSGI container like Flask, Bottle, ... - NOT Saddle - and want to use Skitai asynchronous services, you should import 'was'. Usage is exactly same. But for my convinient, I wrote example codes Saddle version mostly.


Async Requests Service To Backend Servers
-------------------------------------------

Most importance service of 'was' is making requests to HTTP, REST, RPC and several database engines. And this is mostly useful for fast Server Side Rendering with outside resources.

The modules is related theses features from aquests_ and you could read aquests_ usage first.

I think it just fine explains some differences with aquests.

First of all, usage is somewhat different because aquests is used within threadings on skitai. Skitai takes some threading advantages and compromise with them for avoiding callback heaven.

Usage
``````

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
  
  def request (was):
    req1 = was.get (url)
    req2 = was.post (url, {"user": "Hans Roh", "comment": "Hello"})    
    respones1 = req1.getwait (timeout = 3)
    response2 = req2.getwait (timeout = 3)    
    return [respones1.data, respones2.data]

The significant differnce is calling getwait (timeout) for getting response data.

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

Here're addtional methods and properties above response obkect compared with aquests' response one.

- cache (timeout): response caching
- status: it indicate requests processed status and note it is not related response.status_code.

  - 0: Initial Default Value
  - 1: Operation Timeout
  - 2: Exception Occured
  - 3: Normal Terminated

.. _aquests: https://pypi.python.org/pypi/aquests


Methods List
````````````````

All supoorted request methods are:

- Web/API related

  - was.get (): also available shortcuts getjson, getxml
  - was.delete (): also available shortcuts deletejson, deletexml
  - was.post (): also available shortcuts postjson, postxml
  - was.put (): also available shortcuts putjson, putxml
  - was.patch (): also available shortcuts patchjson, patchxml
  - was.options ()

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

If you run Skitai with single threaded mode, you can't use req.wait(), req.getwait() or req.getswait(). Instead you should use callback for this, and Skitai provide async response.

.. code:: python
  
  def promise_handler (promise, response):
    promise.settle (response.content)
        
  @app.route ("/index")
  def promise_example (was):
    promise = was.promise (promise_handler)    
    promise.get (None, "https://pypi.python.org/pypi/skitai")    
    return promise

Unfortunately this feature is available on Skito-Saddle WSGI container only (It means Flask or other WSGI container users can only use Skitai with multi-threading mode). 

For more detail usage will be explained 'Skito-Saddle Async Streaming Response' chapter and you could skip now.


Load-Balancing
````````````````

Skitai support load-balancing requests.

If server members are pre defined, skitai choose one automatically per each request supporting *fail-over*.

Then let's request XMLRPC result to one of mysearch members.
   
.. code:: python

  @app.route ("/search")
  def search (was, keyword = "Mozart"):
    s = was.rpc.lb ("@mysearch/rpc2").search (keyword)
    results = s.getwait (5)
    return result.data
  
  if __name__ == "__main__":
    import skitai
    
    skitai.alias (
      '@mysearch',
       skitai.PROTO_HTTP, 
       ["s1.myserver.com:443", "s2.myserver.com:443"]
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
       skitai.PROTO_HTTP, 
       ["s1.myserver.com:443", "s2.myserver.com:443"]
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
    result = req.getwait (2)
  
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
      results = req.getswait (2)
      
      all_results = []
      for result in results:      
         all_results.extend (result.data)
      return all_results

There are 2 changes:

1. from was.rpc.lb () to was.rpc.map ()
2. from s.getwait () to s.getswait () for multiple results, and results is iterable.


Using Aliased Database
``````````````````````````

If you have alias your database server, you needn't specify db type like 'dbo = was.postgresql ("@mydb")'. Just use 'dbo = was.backend ("@mydb")'.

It makes easy to handle both Sqlite3 and PostgreSQL. If you intend to use Sqlite3 at developing, but use PostgreSQL at production, you just change alias on Skitai startup time.


Caching Result
````````````````

By default, all HTTP requests keep server's cache policy given by HTTP response header (Cache-Control, Expire etc). But you can control cache as your own terms including even database query results.

Every results returned by getwait(), getswait() can cache.

.. code:: python

  s = was.rpc.lb ("@mysearch/rpc2").getinfo ()
  result = s.getwait (2)
  if result.status_code == 200:
    result.cache (60) # 60 seconds
  
  s = was.rpc.map ("@mysearch/rpc2").getinfo ()
  results = s.getswait (2)
  # assume @mysearch has 3 members
  if results.status_code == [200, 200, 200]:
    result.cache (60)

Although code == 200 alredy implies status == 3, anyway if status is not 3, cache() will be ignored. If cached, it wil return cached result for 60 seconds.

*New in version 0.15.28*

If you getwait with reraise argument, code can be simple.

.. code:: python

  s = was.rpc.lb ("@mysearch/rpc2").getinfo ()
  content = s.getswait (2, reraise = True).data
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
  result = s.getwait (2)
  if result.status_code == 200:
    result.cache (60) # 60 seconds  


More About Cache Control: Model Synchronized Cache
`````````````````````````````````````````````````````

*New in version 0.26.15*

`use_cache` value can be True, False or last updated time of base object. If last updated is greater than cached time, cache will be expired immediately and begin new query/request.

You can integrate your models changing and cache control.

First of all, you should set all cache control keys to Skitai for sharing model state beetween worker processes.

.. code:: python

  skitai.addlu ('tables.users', 'table.photos')

These Key names are might be related your database model names nor table names. Especially you bind Django model signal, these keys should be exaclty nodel class name. But in general cases, key names are fine if you easy to recognize.
  
These key names are not mutable and you cannot add new key after calling skitai.run ().
  
Then you can use setlu () and getlu (),

.. code:: python

  app = Saddle (__name__)
  
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

Also was.setlu () emits 'model-changed' events. You can handle event if you need. But this event system only available on Skito-Saddle middle-ware.

.. code:: python
  
  app = Saddle (__name__)
  
  @app.route ("/update")
  def update (was):
    # update users tabale
    was.backend ('@mydb').execute (...)
    # update last update time by key string
    was.setlu ('tables.users', something...)
  
  @app.on_broadcast ("model-changed:tables.users")
  def on_broadcast (was, *args, **kargs):
    # your code

Note: if @app.on_broadcast is located in decorate function at decorative directory, even app.use_reloader is True, it is not applied to app when component file is changed. In this case you should manually reload app by resaving app file.


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

In next chapters' features of 'was' are only available for *Skito-Saddle WSGI container*. So if you have no plan to use Saddle, just skip.


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

- was.status () # HTML formatted status information like phpinfo() in PHP.
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

Websocket messages will be automatically converted to theses objects. Note that option is only available with Skito-Saddle WSGI container.

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
      
At Skito-Saddle, handling events is more simpler,

.. code:: python
  
  if was.wshasevent ():
    if was.wsinit ():
      return was.wsconfig (spec, timeout, message_type)    
    elif was.wsopened ():
      return
    elif was.wsclosed ():
      return  
    return
        

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

  from skitai.saddle import Saddle
  import skitai
  
  app = Saddle (__name__)
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

For your convinient, message automatically load and dump object like JSON. But this feature is only available with Skito-Saddle.

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
  
  app = Saddle (__name__)
  
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


Request Handling with Skito-Saddle
====================================

*Saddle* is WSGI container integrated with Skitai App Engine.

Flask and other WSGI container have their own way to handle request. So If you choose them, see their documentation.

And note below objects and methods *ARE NOT WORKING* in any other WSGI containers except Saddle.

Before you begin, recommended Saddle App's directory structure is like this:

- service.py: Skitai runner
- app.py: File, Main app
- static: Directory, Place static files like css, js, images. This directory should be mounted for using
- decorative: Directory, Module components, utils or helpers for helping app like config.py, model.py etc...
- templates: Directory, Jinaja and Chameleon template files
- resources: Directory, Various files as app need like sqlite db file. In you app, you use these files, you can access file in resources by app.get_resource ("db", "sqlite3.db") like os.path.join manner.


Access Saddle App
------------------

You can access all Saddle object from was.app.

- was.app.debug
- was.app.use_reloader
- was.app.config # use for custom configuration like was.app.config.my_setting = 1

- was.app.securekey
- was.app.session_timeout = None  

- was.app.authorization = "digest"
- was.app.authenticate = False
- was.app.realm = None
- was.app.users = {}
- was.app.jinja_env

- was.app.build_url () is equal to was.ab ()

Currently was.app.config has these properties and you can reconfig by setting new value:

- was.app.config.max_post_body_size = 5 * 1024 * 1024
- was.app.config.max_cache_size = 5 * 1024 * 1024
- was.app.config.max_multipart_body_size = 20 * 1024 * 1024
- was.app.config.max_upload_file_size = 20000000


Debugging and Reloading App
-----------------------------

If debug is True, all errors even server errors is shown on both web browser and console window, otherhwise shown only on console.

If use_reloader is True, Skito-Saddle will detect file changes and reload app automatically, otherwise app will never be reloaded.

.. code:: python

  from skitai.saddle import Saddle
  
  app = Saddle (__name__)
  app.debug = True # output exception information
  app.use_reloader = True # auto realod on file changed


App Package
------------

If app.use_reloader is True, all module of package - sub package directory of app.py - will be reloaded automatically if file is modified.

Saddle will watch default package directory: 'package' and 'contrib'

If you use other packages and need to reload,

.. code:: python
  
  app = Saddle (__name__)
  app.add_package ('mylib', 'corplib')


Routing
--------

Basic routing is like this:

.. code:: python
  
  @app.route ("/hello")
  def hello_world (was):  
    return was.render ("hello.htm")

For adding some restrictions:

.. code:: python
  
  @app.route ("/hello", methods = ["GET"], content_types = ["text/xml"])
  def hello_world (was):  
    return was.render ("hello.htm")

If method is not GET, Saddle will response http error code 405 (Method Not Allowed), and content-type is not text/xml, 415 (Unsupported Content Type).

  
Request
---------

Reqeust object provides these methods and attributes:

- was.request.method # upper case GET, POST, ...
- was.request.command # lower case get, post, ...
- was.request.uri
- was.request.version # HTTP Version, 1.0, 1.1
- was.request.scheme # http or https
- was.request.headers # case insensitive dictioanry
- was.request.body # bytes object
- was.request.args # dictionary merged with url, query string, form data and JSON
- was.request.routed_function
- was.request.routable # {'methods': ["POST", "OPTIONS"], 'content_types': ["text/xml"]}
- was.request.split_uri () # (script, param, querystring, fragment)
- was.request.json () # decode request body from JSON
- was.request.form () # decode request body to dict if content-type is form data
- was.request.dict () # decode request body as dict if content-type is compatible with dict - form data or JSON
- was.request.get_header ("content-type") # case insensitive
- was.request.get_headers () # retrun header all list
- was.request.get_body ()
- was.request.get_scheme () # http or https
- was.request.get_remote_addr ()
- was.request.get_user_agent ()
- was.request.get_content_type ()
- was.request.get_main_type ()
- was.request.get_sub_type ()

Getting Parameters
---------------------

Saddle's parameters are comceptually seperated 3 groups: URL, query string and form data.

Below explaination may be a bit complicated but it is enough to remember 2 things:

1. All parameter groups can be handled same way, there's no differences except origin of prameters
2. Eventaully was.request.args contains all parameters of all origins include default arguments of your resource


Getting URL Parameters
`````````````````````````

URL Parameters should be arguments of resource.

.. code:: python

  @app.route ("/episode/<int:id>")
  def episode (was, id):
    return id
  # http://127.0.0.1:5000/episode

for fancy url building, available param types are:

- int
- float
- path: /download/<int:major_ver>/<path>, should be positioned at last like /download/1/version/1.1/win32
- If not provided, assume as string. and all space will be replaced to "_"

It is also possible via keywords args,

.. code:: python

  @app.route ("/episode/<int:id>")
  def episode (was, \*\*karg):
    retrun was.request.args.get ("id")
  # http://127.0.0.1:5000/episode
  
Query String Parameters
``````````````````````````````

qiery string parameter can be both resource arguments but needn't be.

.. code:: python
  
  @app.route ("/hello")
  def hello_world (was, num = 8):
    return num
  # http://127.0.0.1:5000/hello?num=100  

It is same as these,
  
.. code:: python

  @app.route ("/hello")
  def hello_world (was):
    return was.request.args.get ("num")
  
  @app.route ("/hello")
  def hello_world (was, **url):
    return url.get ("num")

Above 2 code blocks have a significant difference. First one can get only 'topic' parameter. If URL query string contains other parameters, Skitai will raise 508 Error. But 2nd one can be any parameters.
    
Getting Form/JSON Parameters
```````````````````````````````

Getting form is not different from the way for url parameters, but generally form parameters is too many to use with each function parameters, can take from single args \*\*form or take mixed with named args and \*\*form both.
if request header has application/json 

.. code:: python

  @app.route ("/hello")
  def hello (was, **form):
    return "Post %s %s" % (form.get ("userid", ""), form.get ("comment", ""))
    
  @app.route ("/hello")
  def hello_world (was, userid, **form):
    return "Post %s %s" % (userid, form.get ("comment", ""))

Note that for receiving request body via arguments, you specify keywords args like \*\*karg or specify parameter names of body data.

If you want just handle POST body, you can use was.request.json () or was.request.form () that will return dictionary object.
  
Getting Composed Parameters
```````````````````````````````

You can receive all type of parameters by resource arguments. Let'assume yotu resource URL is http://127.0.0.1:5000/episode/100?topic=Python.

.. code:: python
  
  @app.route ("/episode/<int:id>")
  def hello (was, id, topic):
    pass

if URL is http://127.0.0.1:5000/episode/100?topic=Python with Form/JSON data {"comment": "It is good idea"}

.. code:: python
  
  @app.route ("/episode/<int:id>")
  def hello (was, id, topic, comment):
    pass
    
Note that argument should be ordered by:

- URL parameters
- URL query string
- Form/JSON body

And note if your request has both query string and form/JSON body, and want to receive form paramters via arguments, you should receive query string parameters first. It is not allowed to skip query string.

Also you can use keywords argument.

.. code:: python
    
  @app.route ("/episode/<int:id>")
  def hello (was, id, \*\*karg):
    karg.get ('topic')

Note that \*\*karg is contains both query string and form/JSON data and no retriction for parameter names.

was.requests.args is merged dictionary for all type of parameters. If parameter name is duplicated, its value will be set to form of value list. Then simpletst way for getting parameters, use was.requests.args.

.. code:: python
  
  @app.route ("/episode/<int:id>")
  def hello (was, id):
    was.request.args.get ('topic')


Make Your Own Principal
``````````````````````````

I prefer these style:

1. In template, access via was.request.args only
2. Otherwise, use arguments for URL & query string parameter, and \*\*args for Form/JSON parameters
3. If paramteres are same and just request method is optional, use arguments or \*\*args


Response
-------------

Basically, just return contents.

.. code:: python
  
  @app.route ("/hello")
  def hello_world (was):  
    return was.render ("hello.htm")

If you need set additional headers or HTTP status,
    
.. code:: python
  
  @app.route ("/hello")
  def hello (was):  
    return was.response ("200 OK", was.render ("hello.htm"), [("Cache-Control", "max-age=60")])

  def hello (was):  
    return was.response (body = was.render ("hello.htm"), headers = [("Cache-Control", "max-age=60")])

  def hello (was):         
    was.response.set_header ("Cache-Control", "max-age=60")
    return was.render ("hello.htm")

Above 3 examples will make exacltly same result.

Sending specific HTTP status code,

.. code:: python
  
  def hello (was):  
    return was.response ("404 Not Found", was.render ("err404.htm"))
  
  def hello (was):
    # if body is not given, automaticcally generated with default error template.
    return was.response ("404 Not Found")

If app raise exception, traceback information will be displayed only app.debug = True. But you intentionally send it inspite of app.debug = False:

.. code:: python
  
  # File
  @app.route ("/raise_exception")
  def raise_exception (was):  
    try:
      raise ValueError ("Test Error")
    except:      
      return was.response ("500 Internal Server Error", exc_info = sys.exc_info ())
    
You can return various objects.

.. code:: python
  
  # File
  @app.route ("/streaming")
  def streaming (was):  
    return was.response ("200 OK", open ("mypicnic.mp4", "rb"), headers = [("Content-Type", "video/mp4")])
  
  # Generator
  def build_csv (was):  
    def generate():
      for row in iter_all_rows():
        yield ','.join(row) + '\n'
    return was.response ("200 OK", generate (), headers = [("Content-Type", "text/csv")])   


All available return types are:

- String, Bytes, Unicode
- File-like object has 'read (buffer_size)' method, optional 'close ()'
- Iterator/Generator object has 'next() or _next()' method, optional 'close ()' and shoud raise StopIteration if no more data exists.
- Something object has 'more()' method, optional 'close ()'
- Classes of skitai.lib.producers
- List/Tuple contains above objects
- XMLRPC dumpable object for if you want to response to XMLRPC

The object has 'close ()' method, will be called when all data consumed, or socket is disconnected with client by any reasons.

- was.response (status = "200 OK", body = None, headers = None, exc_info = None)
- was.response.throw (status = "200 OK"): abort handling request, generated contents and return http error immediatly

- was.response.api (\_\_data_dict\_\_ = None, \*\*kargs): return api response container
- was.response.fault (msg, code = 20000,  debug = None, more_info = None, exc_info = None): return api response container with setting error information
- was.response.traceback (msg = "", code = 10001,  debug = 'see traceback', more_info = None): return api response container with setting traceback info
- was.response.for_api (status = "200 OK",\*args, \*\*kargs): shortcut for was.response (status, was.response.api (...)) if status code is 2xx and was.response (status, was.response.fault (...))

- was.response.set_status (status) # "200 OK", "404 Not Found"
- was.response.get_status ()
- was.response.set_headers (headers) # [(key, value), ...]
- was.response.get_headers ()
- was.response.set_header (k, v)
- was.response.get_header (k)
- was.response.del_header (k)
- was.response.hint_promise (uri) # *New in version 0.16.4*, only works with HTTP/2.x and will be ignored HTTP/1.x


File Stream 
`````````````
Response provides some methods for special objects.

First of all, for send a file, 

.. code:: python

  @app.route ("/<filename>")
  def getfile (was, filename):  
    return was.response.file ('/data/%s' % filename)    


JSON API Response
````````````````````
*New in version 0.26.15.9*

In cases you want to retrun JSON API reponse,

.. code:: python
  
  # return JSON {data: [1,2,3]}
  return was.response.for_api ('200 OK', data = [1, 2, 3])
  # return empty JSON {}
  return was.response.for_api (201 Accept')
  
  # and shortcut if response HTTP status code is 200 OK,
  return was.response.api (data =  [1, 2, 3])
  
  # return empty JSON {}
  return was.response.api ()
  
For sending error response with error information,

.. code:: python
  
  # client will get, {"message": "parameter q required", "code": 10021}
  return was.response.for_api ('400 Bad Request', 'missing parameter', 10021)  
  
  # with additional information,
  was.response.for_api (
  	'400 Bad Request',
  	'missing parameter', 10021, 
    'need parameter offset and limit', # detailed debug information
    'http://127.0.0.1/moreinfo/10021', # more detail URL something    
  )

You can send traceback information for debug purpose like in case app.debug = False,

.. code:: python
  
  try:
    do something
  except:
    return was.response.traceback ('somethig is not valid') 

  # client see,
  {
    "code": 10001,
    "message": "somethig is not valid",
    "debug": "see traceback", 
    "traceback": [
      "name 'aa' is not defined", 
      "in file app.py at line 276, function search"      
    ]
  }

Important note that this response will return with HTTP 200 OK status. If you want return 500 code, just let exception go.

But if your client send header with 'Accept: application/json' and app.debug is True, Skitai returns traceback information automatically.


Async Promise Response
--------------------------

*New in version 0.24.8*

If you use was' requests services, and they're expected taking a long time to fetch, you can use async response.

- Async promise response has advantage at multi threads environment returning current thread to thread pool early for handling the other requests
- Async promise response should be used at single thread evironment. If you run Skitai with threads = 0, you can't use wait(), getwait() or getswiat() for receiving response for HTTP/DBO requests.
- Unlike general promises, Skitai promise handle multiple funtions with only single handler.

.. code:: python
  
  def promise_handler (promise, resp):
    if resp.status_code == 200:
      promise [resp.id]  = promise.render (
        '%s.html' % resp.id,
        data = response.json ()
      )
    else:
      promise [resp.id] = '<div>Error in %s</div>' % resp.id
     
    # check if all requests are done
    if promise.fulfilled ():    
      promise.settle (promise.render ("final.html"))
      # or just join response data
      # promise.settle (promise ['skitai'] + "<hr>" + promise ['aquests'])

  @app.route ("/promise")
  def promise (was):
    promise = was.promise (promise_handler, A = "123", B = "456")
    promise.get ('C', "https://pypi.python.org/pypi/skitai")
    promise.get ('D', "https://pypi.python.org/pypi/aquests")
    return promise

Database query example,
    
.. code:: python
  
  def promise_handler (promise, resp):   
    if promise.fulfilled ():
      r = promise ["stats"]
      r ['result'] = resp.data
      promise.settle (promise.response.api (r))

  @app.route ("/promise")
  def promise (was):
    promise = was.promise (promise_handler, stats = {'total': 100})
    promise.backend ('query', "@postgre").execute ("select ...")
    return promise
    
'skitai.html' Jinja2 template used in render() is,

.. code:: html

  <div>{{ r.url }} </div>
  <div>{{ r.text }}</div>

'example.html' Jinja2 template used in render() is,

.. code:: html
  
  <h1>{{ A }} of {{ B }}</h1>
  <div>{{ C }}</div>
  <hr>
  <div>{{ D }}</div>

And you can use almost was.* objects at render() and render() like was.request, was.app, was.ab or was.g etc. But remember that response header had been already sent so you cannot use aquests features and connot set new header values like cookie or mbox (but reading is still possible).
  
Above proxy can make requests as same as was object except first argument is identical request name (reqid). Compare below things.

  * was.get ("https://pypi.python.org/pypi/skitai")
  * Promise.get ('skitai', "https://pypi.python.org/pypi/skitai")

This identifier can handle responses at executing callback. reqid SHOULD follow Python variable naming rules because might be used as template variable.

You MUST call Promise.settle (content_to_send) finally, and if you have chunk content to send, you can call Promise.send(chunk_content_to_send) for sending middle part of contents before calling settle ().

*New in version 0.25.2*

You can set meta data dictionary per requests if you need.

.. code:: python

  def promise_handler (promise, response):
    due = time.time () - response.meta ['created']
    promise.send (response.content)
    promise.send ('Fetch in %2.3f seconds' % due)
    promise.settle () # Should call
    
  @app.route ("/promise")
  def promise (was):
    promise = was.promise (promise_handler)
    promise.get ('req-0', "http://my-server.com", meta = {'created': time.time ()})    
    return was.response ("200 OK", promise, [('Content-Type', 'text/plain')])

But it is important that meta arg should be as keyword arg, and DON'T use 'reqid' as meta data key. 'reqid' is used internally.

    
Creating async response proxy:

- was.promise (promise_handler, prolog = None, epilog = None): return Promise, prolog and epilog is like html header and footer

response_handler should receive 2 args: response for your external resource request and Promise.

Note: It's impossible requesting map-reduce requests at async response mode.

collect_producer has these methods.

- Promise (handler, keyword args, ...)
- Promise.get (reqid, url, ...), post (reqid, url, data, ...) and etc
- Promise.set (name, data): save data for generating full contents
- Promise.pending (): True if numer of requests is not same as responses
- Promise.fulfilled (): True if numer of requests is same as responses
- Promise.settled (): True if settle () is called
- Promise.rejected (): ignore all response after called
- Promise.render (template_file, single dictionary object or keyword args, ...): render each response, if no args render with promise's data set before
- Promise.send (content_to_send): push chunk data to channel
- Promise.settle (content_to_send = None)
- Promise.reject (content_to_send = None)


App Decorating: Making Simpler & Modular App
----------------------------------------------------

*New in version 0.26.17*

You can split yours views and help utilties into decorative directory.

Assume your application directory structure is like this,

.. code:: bash

  templates/*.html  
  decorative/*.py # app library, all modules in this directory will be watched for reloading  
  static/images # static files
  static/js
  static/css
  
  app.py # this is starter script  

app.py
  
.. code:: python

  from decorative import auth
  
  app = Saddle (__name__)

  app.debug = True
  app.use_reloader = True

  @app.default_error_handler
  def default_error_handler (was, e):
    return str (e)
    
decorative/auth.py

.. code:: python
  
  # shared utility functions used by views
  
  def titlize (s):
    ...
    return s
  
  # decorate on app

  def decorate (app):  
    @app.login_handler
    
  def login_handler (was):  
    if was.session.get ("username"):
      return
    next_url = not was.request.uri.endswith ("signout") and was.request.uri or ""    
    return was.redirect (was.ab ("signin", next_url))
    
  @app.route ("/signout")
  def signout (was):
    was.session.remove ("username")
    was.mbox.push ("Signed out successfully", "success")  
    return was.redirect (was.ab ('index'))
    
  @app.route ("/signin")
  def signin (was, next_url = None, **form):
    if was.request.args.get ("username"):
      user = auth.authenticate (was.django, username = was.request.args ["username"], password = was.request.args ["password"])
      if user:
        was.session.set ("username", was.request.args ["username"])
        return was.redirect (was.request.args ["next_url"])
      else:
        was.mbox.push ("Invalid User Name or Password", "error", icon = "new_releases")
    return was.render ("sign/signin.html", next_url = next_url or was.ab ("index"))

You just import module from decorative. but *def decorate (app)* is core in each module. Every modules can have *decorate (app)* in *decorative*, so you can split and modulize views and utility functions. decorate (app) will be automatically executed on starting. If you set app.use_reloader, theses decorative will be automatically reloaded and re-executed on file changing. Also you can make global app sharable functions into seperate module like util.py without views.

If you need parameters on decorating,

.. code:: python

  def decorate (app, prefix):
    @app.route (prefix + "/login")
    def login (was):
      ...

And on app, 
      
.. code:: python

  from decorative import auth
  
  app = Saddle (__name__)
  app.decorate_with (auth, '/regist')


Using Websocket
-------------------

*New in version 0.26.18*

Websokect usage is already explained, but Saddle provide @app.websocket_config decorator for more elegant way to use it.

.. code:: python

  def onopen (was):
    print ('websocket opened')

  def onclose (was):
    print ('websocket closed')
    
  @app.route ("/websocket")
  @app.websocket_config (skitai.WS_THREADSAFE, 1200, onopen, onclose)
  def websocket (was, message):
    return 'you said: ' + message

This decorator spec is,

.. code:: python
     
  @app.websocket_config (
    spec, # one of skitai.WS_SIMPLE, skitai.WS_THREADSAFE and skitai.WS_GROUPCHAT	 
    timeout = 60, 
    onopen = None, 
    onclose = None 
  )


HTTP/2.0 Server Push
-----------------------

*New in version 0.16*

Skiai supports HTPT2 both 'h2' protocl over encrypted TLS and 'h2c' for clear text (But now Sep 2016, there is no browser supporting h2c protocol).

Basically you have nothing to do for HTTP2. Client's browser will handle it except `HTTP2 server push`_.

For using it, you just call was.response.hint_promise (uri) before return response data. It will work only client browser support HTTP2, otherwise will be ignored.

.. code:: python

  @app.route ("/promise")
  def promise (was):
  
    was.response.hint_promise ('/images/A.png')
    was.response.hint_promise ('/images/B.png')
    
    return was.response (
      "200 OK", 
      (
        'Promise Sent<br><br>'
        '<img src="/images/A.png">'
        '<img src="/images/B.png">'
      )
    )  

.. _`HTTP2 server push`: https://tools.ietf.org/html/rfc7540#section-8.2
    
Building URL
---------------

If your app is mounted at "/math",

.. code:: python

  @app.route ("/add")
  def add (was, num1, num2):  
    return int (num1) + int (num2)
    
  was.app.build_url ("add", 10, 40) # returned '/math/add?num1=10&num2=40'
  
  # BUT it's too long to use practically,
  # was.ab is acronym for was.app.build_url
  was.ab ("add", 10, 40) # returned '/math/add?num1=10&num2=40'
  was.ab ("add", 10, num2=60) # returned '/math/add?num1=10&num2=60'
  
  @app.route ("/hello/<name>")
  def hello (was, name = "Hans Roh"):
    return "Hello, %s" % name
  
  was.ab ("hello", "Your Name") # returned '/math/hello/Your_Name'



Access Environment Variables
------------------------------

was.env is just Python dictionary object.

.. code:: python

  if "HTTP_USER_AGENT" in was.env:
    ...
  was.env.get ("CONTENT_TYPE")


Jinja2 Template Engine
------------------------

Although You can use any template engine, Skitai provides was.render() which uses Jinja2_ template engine. For providing arguments to Jinja2, use dictionary or keyword arguments.

.. code:: python
  
  return was.render ("index.html", choice = 2, product = "Apples")
  
  #is same with:
  
  return was.render ("index.html", {"choice": 2, "product": "Apples"})
  
  #BUT CAN'T:
  
  return was.render ("index.html", {"choice": 2}, product = "Apples")


Directory structure sould be:

- /project_home/app.py
- /project_home/templates/index.html


At template, you can use all 'was' objects anywhere defautly. Especially, Url/Form parameters also can be accessed via 'was.request.args'.

.. code:: html
  
  {{ was.cookie.username }} choices item {{ was.request.args.get ("choice", "N/A") }}.
  
  <a href="{{ was.ab ('checkout', choice) }}">Proceed</a>

Also 'was.g' is can be useful in case threr're lots of render parameters.

.. code:: python

  was.g.product = "Apple"
  was.g.howmany = 10
  
  return was.render ("index.html")

And at jinja2 template, 
  
.. code:: html
  
  {% set g = was.g }} {# make shortcut #}
  Checkout for {{ g.howmany }} {{ g.product }}{{g.howmany > 1 and "s" or ""}}
  

If you want modify Jinja2 envrionment, can through was.app.jinja_env object.

.. code:: python
  
  def generate_form_token ():
    ...
    
  was.app.jinja_env.globals['form_token'] = generate_form_token


*New in version 0.15.16*

Added new app.jinja_overlay () for easy calling app.jinja_env.overlay ().

Recently JS HTML renderers like Vue.js, React.js have confilicts with default jinja mustache variable. In this case you mightbe need change it.

.. code:: python

  app = Saddle (__name__)
  app.debug = True
  app.use_reloader = True
  app.jinja_overlay (
    variable_start_string = "{{", 
    variable_end_string = "}}", 
    block_start_string = "{%", 
    block_end_string = "%}",
    comment_start_string = "{#",
    comment_end_string = "#}",
    line_statement_prefix = "%",
    line_comment_prefix = "%%"
  )

if you set same start and end string, please note for escaping charcter, use double escape. for example '#', use '##' for escaping.

*Warning*: Current Jinja2 2.8 dose not support double escaping (##) but it will be applied to runtime patch by Saddle. So if you use app.jinja_overlay, you have compatible problems with official Jinja2.

.. _Jinja2: http://jinja.pocoo.org/


Chameleon Template Engine
----------------------------

*New in version 0.26.6*

*Note added in version 0.26.12*: I don't know it is my fault, but Chameleon is unstable with multithreading environment (or heavy under load) on win32 and even crash Skitai. I recommend do not use it with these environment. And Chameleon will not be installed when pip install. If you need this one, install manually.

For using Chameleon_ template engine, you just make template file extention with '.pt' or '.ptal' (Page Template or Page Template Attribute Language).

I personally prefer Chameleon with `Vue.js`_ for HTML rendering.

.. code:: python
    
  return was.render (
    "index.ptal", 
    dashboard = [
      {'population': 235642, 'school': 34, 'state': 'NY', 'nation': 'USA'}, 
      {'population': 534556, 'school': 54, 'state': 'BC', 'nation': 'Canada'}, 
       ]
     )

Here's example part of index.ptal.

.. code:: html
  
  ${ was.request.args ['query'] }
  
  <tr tal:repeat="each dashboard">
    <td>
      <a tal:define="entity_name '%s, %s' % (each ['state'], each ['nation'])" 
         tal:attributes="href was.ab ('entities', was.request.args ['level'], each ['state'])" 
         tal:content="entity_name">
      </a>
    </td>
    <td tal:content="each ['population']" />
    <td>${ each ['schools'] }</td>    
  </tr>

.. _`Vue.js`: https://vuejs.org/


Custom Error Template
-----------------------

*New in version 0.26.7*

.. code:: python

  @app.default_error_handler
  def not_found (was, error):
    return was.render ('default.htm', error = error)

  @app.error_handler (404)
  def not_found (was, error):
    return was.render ('404.htm', error = error)

Template file 404.html is like this:

.. code:: html

  <h1>{{ error.code }} {{ error.message }}</h1>  
  <p>{{ error.detail }}</p>
  <hr>
  <div>URL: {{ error.url }}</div>
  <div>Time: {{ error.time }}</div>  

Note that custom error templates can not be used before routing to the app.

Access Cookie
----------------

was.cookie has almost dictionary methods.

.. code:: python

  if "user_id" not in was.cookie:
    was.cookie.set ("user_id", "hansroh")    
    # or    
    was.cookie ["user_id"] = "hansroh"


*Changed in version 0.15.30*

'was.cookie.set()' method prototype has been changed.

.. code:: python

  was.cookie.set (
    key, val, 
    expires = None, 
    path = None, domain = None, 
    secure = False, http_only = False
  ) 

'expires' args is seconds to expire. 

 - if None, this cookie valid until browser closed
 - if 0 or 'now', expired immediately
 - if 'never', expire date will be set to a hundred years from now

If 'secure' and 'http_only' options are set to True, 'Secure' and 'HttpOnly' parameters will be added to Set-Cookie header.

If 'path' is None, every app's cookie path will be automaticaaly set to their mount point.

For example, your admin app is mounted on "/admin" in configuration file like this:

.. code:: python

  app = ... ()
  
  if __name__ == "__main__": 
  
    import skitai
    
    skitai.run (
      address = "127.0.0.1",
      port = 5000,
      mount = {'/admin': app}
    )

If you don't specify cookie path when set, cookie path will be automatically set to '/admin'. So you want to access from another apps, cookie should be set with upper path = '/'.

.. code:: python
  
  was.cookie.set ('private_cookie', val)
        
  was.cookie.set ('public_cookie', val, path = '/')
    
- was.cookie.set (key, val, expires = None, path = None, domain = None, secure = False, http_only = False)
- was.cookie.remove (key, path, domain)
- was.cookie.clear (path, domain)
- was.cookie.keys ()
- was.cookie.values ()
- was.cookie.items ()
- was.cookie.has_key ()


Access Session
----------------

was.session has almost dictionary methods.

To enable session for app, random string formatted securekey should be set for encrypt/decrypt session values.

*WARNING*: `securekey` should be same on all skitai apps at least within a virtual hosing group, Otherwise it will be serious disaster.

.. code:: python

  app.securekey = "ds8fdsflksdjf9879dsf;?<>Asda"
  app.session_timeout = 1200 # sec
  
  @app.route ("/session")
  def hello_world (was, **form):  
    if "login" not in was.session:
      was.session.set ("user_id", form.get ("hansroh"))
      # or
      was.session ["user_id"] = form.get ("hansroh")

If you set, alter or remove session value, session expiry is automatically extended by app.session_timeout. But just getting value will not be extended. If you extend explicit without altering value, you can use touch() or set_expiry(). session.touch() will extend by app.session_timeout. session.set_expiry (timeout) will extend by timeout value.

Once you set expiry, session auto extenstion will be disabled until expiry time become shoter than new expiry time is calculated by app.session_timeout.  

- was.session.set (key, val)
- was.session.get (key, default = None)
- was.session.source_verified (): If current IP address matches with last IP accesss session
- was.session.getv (key, default = None): If not source_verified (), return default
- was.session.remove (key)
- was.session.clear ()
- was.session.keys ()
- was.session.values ()
- was.session.items ()
- was.session.has_key ()
- was.session.set_expiry (timeout)
- was.session.touch ()
- was.session.expire ()


Messaging Box
----------------

Like Flask's flash feature, Skitai also provide messaging tool.

.. code:: python  

  @app.route ("/msg")
  def msg (was):
    was.mbox.send ("This is Flash Message", "flash")
    was.mbox.send ("This is Alert Message Kept by 60 seconds on every request", "alram", valid = 60)
    return was.redirect (was.ab ("showmsg", "Hans Roh"), status = "302 Object Moved")
  
  @app.route ("/showmsg")
  def showmsg (was, name):
    return was.render ("msg.htm", name=name)
    
A part of msg.htm is like this:

.. code:: html

  Messages To {{ name }},
  <ul>
    {% for message_id, category, created, valid, msg, extra in was.mbox.get () %}
      <li> {{ mtype }}: {{ msg }}</li>
    {% endfor %}
  </ul>

Default value of valid argument is 0, which means if page called was.mbox.get() is finished successfully, it is automatically deleted from mbox.

But like flash message, if messages are delayed by next request, these messages are save into secured cookie value, so delayed/long term valid messages size is limited by cookie specificatio. Then shorter and fewer messsages would be better as possible.

'was.mbox' can be used for general page creation like handling notice, alram or error messages consistently. In this case, these messages (valid=0) is consumed by current request, there's no particular size limitation.

Also note valid argument is 0, it will be shown at next request just one time, but inspite of next request is after hundred years, it will be shown if browser has cookie values.

.. code:: python  
  
  @app.before_request
  def before_request (was):
    if has_new_item ():
      was.mbox.send ("New Item Arrived", "notice")
  
  @app.route ("/main")  
  def main (was):
    return was.render ("news.htm")

news.htm like this:

.. code:: html

  News for {{ was.g.username }},
  <ul>
    {% for mid, category, created, valid, msg, extra in was.mbox.get ("notice", "news") %}
      <li class="{{category}}"> {{ msg }}</li>
    {% endfor %}
  </ul>

- was.mbox.send (msg, category, valid_seconds, key=val, ...)
- was.mbox.get () return [(message_id, category, created_time, valid_seconds, msg, extra_dict)]
- was.mbox.get (category) filtered by category
- was.mbox.get (key, val) filtered by extra_dict
- was.mbox.source_verified (): If current IP address matches with last IP accesss mbox
- was.mbox.getv (...) return get () if source_verified ()
- was.mbox.search (key, val): find in extra_dict. if val is not given or given None, compare with category name. return [message_id, ...]
- was.mbox.remove (message_id)


Named Session & Messaging Box
------------------------------

*New in version 0.15.30*

You can create multiple named session and mbox objects by mount() methods.

.. code:: python

  was.session.mount (
    name = None, securekey = None, 
    path = None, domain = None, secure = False, http_only = False, 
    session_timeout = None
   )
  
  was.mbox.mount (
    name = None, securekey = None, 
    path = None, domain = None, secure = False, http_only = False
  )


For example, your app need isolated session or mbox seperated default session for any reasons, can create session named 'ADM' and if this session or mbox is valid at only /admin URL.

.. code:: python

  @app.route("/")
  def index (was):   
    was.session.mount ("ADM", SECUREKEY_STRING, path = '/admin')
    was.session.set ("admin_login", True)

    was.mbox.mount ("ADM", SECUREKEY_STRING, path = '/admin')
    was.mbox.send ("10 data has been deleted", 'warning')

SECUREKEY_STRING needn't same with app.securekey. And path, domain, secure, http_only args is for session cookie, you can mount any named sessions or mboxes with upper cookie path and upper cookie domain. In other words, to share session or mbox with another apps, path should be closer to root (/).

.. code:: python

  @app.route("/")
  def index (was):   
    was.session.mount ("ADM", SECUREKEY_STRING, path = '/')
    was.session.set ("admin_login", True)

Above 'ADM' sesion can be accessed by all mounted apps because path is '/'.
    
Also note was.session.mount (None, SECUREKEY_STRING) is exactly same as mounting default session, but in this case SECUREKEY_STRING should be same as app.securekey.

mount() is create named session or mbox if not exists, exists() is just check wheather exists named session already.

.. code:: python

  if not was.session.exists (None):
    return "Your session maybe expired or signed out, please sign in again"
      
  if not was.session.exists ("ADM"):
    return "Your admin session maybe expired or signed out, please sign in again"



File Upload
---------------

.. code:: python
  
  FORM = """
    <form enctype="multipart/form-data" method="post">
    <input type="hidden" name="submit-hidden" value="Genious">   
    <p></p>What is your name? <input type="text" name="submit-name" value="Hans Roh"></p>
    <p></p>What files are you sending? <br />
    <input type="file" name="file">
    </p>
    <input type="submit" value="Send"> 
    <input type="reset">
  </form>
  """
  
  @app.route ("/upload")
  def upload (was, *form):
    if was.request.command == "get":
      return FORM
    else:
      file = form.get ("file")
      if file:
        file.save ("d:\\var\\upload", dup = "o") # overwrite
        
'file' object's attributes are:

- file.path: temporary saved file full path
- file.name: original file name posted
- file.size
- file.mimetype
- file.remove ()
- file.save (into, name = None, mkdir = False, dup = "u")

  * if name is None, used file.name
  * dup: 
    
    + u - make unique (default)
    + o - overwrite


Using SQL Map with SQLPhile
-----------------------------

*New in Version 0.26.13*

SQLPhile_ is SQL generator and can be accessed from was.sqlmap.

If you want to use SQL templates, create sub directory 'sqlmaps' and place sqlmap files.

.. code:: python
  
  app.config.sqlmap_engine = "postgresql"  
  
  @app.route ("/")
  def index (was):
    q = was.sqlmap.ops.select ('rc_file', 'id', 'name')
    q.filter (id = 4)
    req = was.backend ("@db").execute (q)
    result = req.getwait ()

Please, visit SQLPhile_ for more detail. 
    
.. _SQLPhile: https://pypi.python.org/pypi/sqlphile


Registering Per Request Calling Functions
-------------------------------------------

Method decorators called automatically when each method is requested in a app.

.. code:: python

  @app.before_request
  def before_request (was):
    if not login ():
      return "Not Authorized"
  
  @app.finish_request
  def finish_request (was):
    was.g.user_id    
    was.g.user_status
    ...
  
  @app.failed_request
  def failed_request (was, exc_info):
    was.g.user_id    
    was.g.user_status
    ...
  
  @app.teardown_request
  def teardown_request (was):
    was.g.resouce.close ()
    ...
  
  @app.route ("/view-account")
  def view_account (was, userid):
    was.g.user_id = "jerry"
    was.g.user_status = "active"
    was.g.resouce = open ()
    return ...

For this situation, 'was' provide was.g that is empty class instance. was.g is valid only in current request. After end of current request.

If view_account is called, Saddle execute these sequence:

.. code:: python
  
  try:
    try: 
      content = before_request (was)
      if content:
        return content
      content = view_account (was, *args, **karg)
      
    except:
      content = failed_request (was, sys.exc_info ())
      if content is None:
        raise
      
    else:
      finish_request (was)

  finally:
    teardown_request (was)
  
  return content
    
Be attention, failed_request's 2nd arguments is sys.exc_info (). Also finish_request and teardown_request (NOT failed_request) should return None (or return nothing). 

If you handle exception with failed_request (), return custom error content, or exception will be reraised and Saddle will handle exception.

*New in version 0.14.13*

.. code:: python

  @app.failed_request
  def failed_request (was, exc_info):
    # releasing resources
    return was.response (
      "501 Server Error", 
      was.render ("err501.htm", msg = "We're sorry but something's going wrong")
    )


App Lifecycle Hook
----------------------

These app life cycle methods will be called by this order,

- before_mount (wac): when app imported on skitai server started
- mounted (*was*): called first with was (instance of wac)
- loop whenever app is reloaded,
  
  - oldapp.before_umount (*was*): when app.use_reloader is True and app is reloaded. it is for shutting down current app
  - oldapp.umounted (wac): when app.use_reloader is True and app is reloaded. it is for shutting down current app
  - newapp.before_remount (wac)
  - newapp.remounted (*was*)
  
- before_umount (*was*): called last with was (instance of wac), add shutting down process
- umounted (wac): when skitai server enter shutdown process

Please note that first arg of startup, reload and shutdown is *wac* not *was*. *wac* is Python Class object of 'was', so mainly used for sharing Skitai server-wide object via was.object before instancelizing to *was*.

.. code:: python

  @app.before_mount
  def before_mount (wac):
    logger = wac.logger.get ("app")
    # OR
    logger = wac.logger.make_logger ("login", "daily")
    config = wac.config
    wac.register ("loginengine", SNSLoginEngine (logger))
    wac.register ("searcher", FulltextSearcher (wac.numthreads))    
  
  @app.before_remount  
  def before_remount (wac):
    wac.loginengine.reset ()
  
  @app.umounted
  def before_umount (wac):
    wac.umounted.close ()
        
    wac.unregister ("loginengine")
    wac.unregister ("searcher")

You can access numthreads, logger, config from wac.

As a result, myobject can be accessed by all your current app functions even all other apps mounted on Skitai.

.. code:: python
  
  # app mounted to 'abc.com/register'
  @app.route ("/")
  def index (was):
    was.loginengine.check_user_to ("facebook")
    was.searcher.query ("ipad")
  
  # app mounted to 'def.com/'
  @app.route ("/")
  def index (was):
    was.searcher.query ("news")

*Note:* The way to mount with host, see *'Mounting With Virtual Host'* chapter below.

It maybe used like plugin system. If a app which should be mounted loads pulgin-like objects, theses can be used by Skitai server wide apps via was.object1, was.object2,...

*New in version 0.26*

If you have databases or API servers, and want to create cache object on app starting, you can use @app.mounted decorator.

.. code:: python
  
  def create_cache (res):
    d = {}
    for row in res.data:
      d [row.code] = row.name
    app.storage.set ('STATENAMES', d)
  
  @app.mounted
  def mounted (was):
    was.backend ('@mydb', callback = create_cache).execute ("select code, name from states;")    
    # or use REST API
    was.get ('@myapi/v1/states', callback = create_cache)
    # or use RPC
    was.rpc ('@myrpc/rpc2', callback = create_cache).get_states ()
  
  @app.remounted
  def remounted (was):
    mounted (was) # same as mounted
  
  @app.before_umount
  def umount (was):
    was.delete ('@session/v1/sessions', callback = lambda x: None)    
    
But both are not called by request, you CAN'T use request related objects like was.request, was.cookie etc. And SHOULD use callback because these are executed within Main thread.


Registering Global Template Function
--------------------------------------

*New in version 0.26.16*

template_global decorator makes a function possible to use in your template,

.. code:: python

  @app.template_global ("test_global")
  def test (was):  
    return ", ".join.(was.request.args.keys ())

At template,
    
.. code:: html

  {{ test_global () }}

Note that all template global function's first parameter should be *was*. But when calling, you SHOULDN't give *was*.


Registering Jinja2 Filter
--------------------------

*New in version 0.26.16*

template_filter decorator makes a function possible to use in your template,

.. code:: python

  @app.template_filter ("reverse")
  def reverse_filter (s):  
    return s [::-1]

At template,
    
.. code:: html

  {{ "Hello" | reverse }}
    
    
Login and Permission Helper
------------------------------

*New in version 0.26.16*

You can define login & permissoin check handler,

.. code:: python

  @app.login_handler
  def login_handler (was):  
    if was.session.get ("demo_username"):
      return
    
    if was.request.args.get ("username"):
      if not was.csrf_verify ():
        return was.response ("400 Bad Request")
      
      if was.request.args.get ("signin"):
        user, level = authenticate (username = was.request.args ["username"], password = was.request.args ["password"])
        if user:
          was.session.set ("demo_username", user)
          was.session.set ("demo_permission", level)
          return
          
        else:
          was.mbox.send ("Invalid User Name or Password", "error")    
          
    return was.render ("login.html", user_form = forms.DemoUserForm ())

  @app.permission_check_handler
  def permission_check_handler (was, perms):
    if was.session.get ("demo_permission") in perms:
      return was.response ("403 Permission Denied")
  
  @app.staff_member_check_handler
  def staff_check_handler (was):
    if was.session.get ("demo_permission") not in ('staff'):
      return was.response ("403 Staff Permission Required")

And use it for your resources if you need,

.. code:: python

  @app.route ("/")
  @app.permission_required ("admin")  
  @app.login_required
  def index (was):
    return "Hello"
  
  @app.staff_member_required
  def index2 (was):
    return "Hello"

Also you can test if user is valid,

.. code:: python
  
  def is_superuser (was):
    if was.user.username not in ('admin', 'root'):
      reutrn was.response ("403 Permission Denied")
  
  @app.testpass_required (is_superuser)
  def modify_profile (was):
    ...
    
Note that in case all of them, if every thing is OK, it *SHOULD return None, not True*.

    
Cross Site Request Forgery Token (CSRF Token)
------------------------------------------------

*New in version 0.26.16*

At template, insert CSRF Token,

.. code:: html
  
  <form>
  {{ was.csrf_token_input }}
  ...
  </form>

then verify token like this,

.. code:: python

  @app.before_request
  def before_request (was):
    if was.request.args.get ("username"):
      if not was.csrf_verify ():
        return was.response ("400 Bad Request")


Making URL Token For Onetime Link
--------------------------------------

*New in version 0.26.17*

For creatiing onetime link url, you can convert your data to secured token string. 

.. code:: python
  
  @app.route ('/password-reset')
  def password_reset (was)
    if was.request.args ('username'):
      token = was.token ("hans", 3600) # valid within 1 hour 
      pw_reset_url = was.ab ('reset_password', token)
      # send email
      return was.render ('done.html')
     
    if was.request.args ('token'):
      username = was.detoken (was.request.args ['token'])
      if req ['expires'] > time.time ():
        return was.response ('400 Bad Request')      
      username = req ['username']
      # processing password reset
      ...

If you want to expire token explicit, add session token key 

.. code:: python

  # valid within 1 hour and create session token named '_reset_token'
  token = was.token ("hans", 3600, 'rset')  
  >> kO6EYlNE2QLNnospJ+jjOMJjzbw?fXEAKFgGAAAAb2JqZWN0...

  username = was.detoken (token)
  >> "hans"
  
  # if processing is done and for expiring token,
  was.rmtoken (token)
  
        
App Event Handling
---------------------

Most of Saddle's event handlings are implemented with excellent `event-bus`_ library.

*New in version 0.26.16*, *Availabe only on Python 3.5+*

.. code:: python

  from skitai import saddle
  
  @app.on (saddle.app_starting)
  def app_starting_handler (wasc):
    print ("I got it!")
  
  @app.on (saddle.request_failed)
  def request_failed_handler (was, exc_info):
    print ("I got it!")
  
  @app.on (saddle.template_rendering)
  def template_rendering_handler (was, template, params):
    print ("I got it!")

There're some app events.

- saddle.app_starting: required (wasc)
- saddle.app_started: required (wasc)
- saddle.app_restarting: required (wasc)
- saddle.app_restarted: required (wasc)
- saddle.app_mounted: required (was)
- saddle.app_unmounting: required (was)
- saddle.request_failed: required ( was, exc_info)
- saddle.request_success: required (was)
- saddle.request_tearing_down: required (was)
- saddle.request_starting: required (was)
- saddle.request_finished: required (was)
- saddle.template_rendering: required (was, template, template_params_dict)
- saddle.template_rendered: required (was, content)

.. _`event-bus`: https://pypi.python.org/pypi/event-bus


Creating and Handling Custom Event
---------------------------------------

*Availabe only on Python 3.5+*

For creating custom event and event handler,

.. code:: python

  @app.on ("user-updated")
  def user_updated (was, user):
    ...

For emitting,

.. code:: python
    
  @app.route ('/users', methods = ["POST"])
  def users (was):
    args = was.request.json ()
    ...
    
    app.emit ("user-updated", args ['userid'])
    
    return ''

If event hasn't args, you can use `emit_after` decorator,

.. code:: python
    
  @app.route ('/users', methods = ["POST"])
  @app.emit_after ("user-updated")
  def users (was):
    args = was.request.json ()
    ...    
    return ''

Using this, you can build automatic excution chain,

.. code:: python
  
  @app.on ("photo-updated")
  def photo_updated (was):
    ...        
    
  @app.on ("user-updated")
  @app.emit_after ("photo-updated")
  def user_updated (was):
    ...        
      
  @app.route ('/users', methods = ["POST"])
  @app.emit_after ("user-updated")
  def users (was):
    args = was.request.json ()
    ...
    return ''


Cross App Communication & Accessing Resources
----------------------------------------------

Skitai prefer spliting apps to small microservices and mount them each. This feature make easy to move some of your mounted apps move to another machine. But this make difficult to communicate between apps. 

Here's some helpful solutions.


Accessing App Object Properties
`````````````````````````````````

*New in version 0.26.7.2*

You can mount multiple app on Skitai, and maybe need to another app is mounted seperatly.

.. code:: python

  skitai.mount ("/", "main.py")
  skitai.mount ("/query", "search.py")

And you can access from filename of app from each apps,

.. code:: python

  search_app = was.apps ["search"]
  save_path = search_app.config.save_path  


URL Building for Resource Accessing
````````````````````````````````````

*New in version 0.26.7.2*
  
If you mount multiple apps like this,

.. code:: python

  skitai.mount ("/", "main.py")
  skitai.mount ("/search", "search.py")

For building url in `main.py` app from a query function of `search.py` app, you should specify app file name with dot.

.. code:: python

  was.ab ('search.query', "Your Name") # returned '/search/query?q=Your%20Name'
  
And this is exactly same as,

  was.apps ["search"].build_url ("query", "Your Name")  

But this is only functioning between apps are mounted within same host.


Communication with Event
``````````````````````````

*New in version 0.26.10*
*Availabe only on Python 3.5+*

'was' can work as an event bus using app.on_broadcast () - was.broadcast () pair. Let's assume that an users.py app handle only user data, and another photo.py app handle only photos of users.

.. code:: python

  skitai.mount ('/users', 'users.py')
  skitai.mount ('/photos', 'photos.py')

If a user update own profile, sometimes photo information should be updated.

At photos.py, you can prepare for listening to 'user:data-added' event and this event will be emited from 'was'.

.. code:: python
  
  @app.on_broadcast ('user:data-added')
  def refresh_user_cache (was, userid):
    was.sqlite3 ('@photodb').execute ('update ...').wait ()

and uses.py, you just emit 'user:data-added' event to 'was'.

.. code:: python
  
  @app.route ('/users', methods = ["PATCH"])
  def users (was):
    args = was.request.json ()
    was.sqlite3 ('@userdb').execute ('update ...').wait ()
    
    # broadcasting event to all mounted apps
    was.broadcast ('user:data-added', args ['userid'])
    
    return was.response (
      "200 OK", 
      json.dumps ({}), 
      [("Content-Type", "application/json")]
    )

If resource always broadcasts event without args, use `broadcast_after` decorator.

.. code:: python
  
  @app.broadcast_after ('some-event')
  def users (was):
    args = was.request.json ()
    was.sqlite3 ('@userdb').execute ('update ...').wait ()   

Note that this decorator cannot be routed by app.route ().


CORS (Cross Origin Resource Sharing) and Preflight
-----------------------------------------------------

For allowing CORS, you should do 2 things:

- set app.access_control_allow_origin
- allow OPTIONS methods for routing

.. code:: python
  
  app = Saddle (__name__)
  app.access_control_allow_origin = ["*"]
  # OR specific origins
  app.access_control_allow_origin = ["http://www.skitai.com:5001"]
  app.access_control_max_age = 3600
  
  @app.route ("/post", methods = ["POST", "OPTIONS"])
  def post (was):
    args = was.request.json ()  
    return was.jstream ({...})  
    

If you want function specific CORS,

.. code:: python
  
  app = Saddle (__name__)
  
  @app.route (
   "/post", methods = ["POST", "OPTIONS"], 
   access_control_allow_origin = ["http://www.skitai.com:5001"],
   access_control_max_age = 3600
  )
  def post (was):
    args = was.request.json ()  
    return was.jstream ({...})  


WWW-Authenticate
-------------------

*Changed in version 0.15.21*

  - removed app.user and app.password
  - add app.users object has get(username) methods like dictionary  

Saddle provide simple authenticate for administration or perform access control from other system's call.

Authentication On Entire App
```````````````````````````````

.. code:: python

  app = Saddle (__name__)
  
  app.authorization = "digest"
  app.realm = "Partner App Area of mysite.com"
  app.users = {"app": ("iamyourpartnerapp", 0, {'role': 'root'})}
  app.authenticate = True
  
  @app.route ("/hello/<name>")
  def hello (was, name = "Hans Roh"):
    return "Hello, %s" % name

If app.authenticate is True, all routes of app require authorization (default is False).


Authentication On Specific Methods Only
`````````````````````````````````````````

Otherwise you can make some routes requirigng authorization like this:

.. code:: python

  # False is default, you can omit this line
  app.authenticate = False
 
  @app.route ("/hello/<name>", authenticate = True)
  def hello (was, name = "Hans Roh"):
    return "Hello, %s" % name


User Collection
`````````````````

The return of app.users.get (username) can be:

  - (str password, boolean encrypted, obj userinfo)
  - (str password, boolean encrypted)
  - str password

If you use encrypted password, you should use digest authorization and password should encrypt by this way:

.. code:: python
  
  from hashlib import md5
  
  encrypted_password = md5 (
    ("%s:%s:%s" % (username, realm, password)).encode ("utf8")
  ).hexdigest ()

    
If authorization is successful, app can access username and userinfo vi was.request.user.

  - was.request.user.name
  - was.request.user.realm
  - was.request.user.info
  

If your server run with SSL, you can use app.authorization = "basic", otherwise recommend using "digest" for your password safety.



Implementing XMLRPC Service
-----------------------------

Client Side:

.. code:: python

  import aquests
      
  stub = aquests.rpc ("http://127.0.0.1:5000/rpc")
  stub.add (10000, 5000)  
  fetchall ()
  
Server Side:

.. code:: python

  @app.route ("/add")
  def index (was, num1, num2):  
    return num1 + num2

Is there nothing to diffrence? Yes. Saddle app methods are also used for XMLRPC service if return values are XMLRPC dumpable.


Implementing gRPC Service
-----------------------------

Client Side:

.. code:: python
  
  import aquests
  import route_guide_pb2
  
  stub = aquests.grpc ("http://127.0.0.1:5000/routeguide.RouteGuide")
  point = route_guide_pb2.Point (latitude=409146138, longitude=-746188906)
  stub.GetFeature (point)
  aquests.fetchall ()
  

.. code:: python

  from tfserver import cli 
    
  def predict_grpc (was):
    stub = was.grpc ("http://127.0.0.1:5000/tensorflow.serving.PredictionService")	
	  fftseq = getone ()
	  stub = was.grpc ("@tfserver")
	  request = cli.build_request ('model', 'predict', stuff = tensor_util.make_tensor_proto(fftseq.astype('float32'), shape=fftseq.shape))
	  req = stub.Predict (request, 10.0)
	  resp = req.getwait ()
	  return cli.Response (resp.data).scores
  
Server Side:

.. code:: python
  
  import route_guide_pb2
  
  def get_feature (feature_db, point):
    for feature in feature_db:
      if feature.location == point:
        return feature
    return None
    
  @app.route ("/GetFeature")
  def GetFeature (was, point):
    feature = get_feature(db, point)
    if feature is None:
      return route_guide_pb2.Feature(name="", location=point)
    else:
      return feature

  if __name__ == "__main__":

  skitai.mount = ('/routeguide.RouteGuide', app)
  skitai.urn ()


For an example, here's my tfserver_ for Tensor Flow Model Server.
  
For more about gRPC and route_guide_pb2, go to `gRPC Basics - Python`_.

Note: I think I don't understand about gRPC's stream request and response. Does it means chatting style? Why does data stream has interval like GPS data be handled as stream type? If it is chat style stream, is it more efficient that use proto buffer on Websocket protocol? In this case, it is even possible collaborating between multiple gRPC clients.

.. _`gRPC Basics - Python`: http://www.grpc.io/docs/tutorials/basic/python.html
.. _tfserver: https://pypi.python.org/pypi/tfserver


Working with Django
-----------------------

*New in version 0.26.15*

I barely use Django, but recently I have opportunity using Django and it is very fantastic and especially impressive to Django Admin System.

Here are some examples collaborating with Djnago and Saddle.

Before it begin, you should mount Django app,

.. code:: python
  
  # mount django app as backend app likely  
  pref = skitai.pref ()
  pref.use_reloader = True
  pref.use_debug = True
  
  sys.path.insert (0, 'mydjangoapp')
  skitai.mount ("/django", 'mydjangoapp/mydjangoapp/wsgi.py', 'application', pref)
  
  # main app
  skitai.mount ('/', 'app.py', 'app')
  skitai.run ()
  
FYI, you can access Django admin by /django/admin with default django setting.

Using Django Login
```````````````````

Django user model and authentication system can be used in Skitai.
 
*was.django* is an inherited instance of Django's WSGIRequest.

Basically you can use Django request's user and session.

- was.django.user
- was.django.session

Also  have some methods for login integration.

- was.django.authenticate (username, password): return username or None if failed
- was.django.login (username)
- was.django.logout ()
- was.django.update_session_auth_hash (user)

Route Proxing Django Views
``````````````````````````````

If mydjangoapp has photos app, for proxing Django views, 

.. code:: python

  from mydjangoapp.photos import views as photos_views
  
  @app.route ('/hello')
  def django_hello (was):
    return photos_views.somefunc (was.django)

Using Django Models
`````````````````````

You can use also Django models.

First of all, you should mount Django app.

.. code:: python

  skitai.mount ("/", "myapp/wsgi.py", "application", pref = pref)

Or you can just use Django models only,

.. code:: python

  skitai.use_django_models ("myapp/settings.py")
  
Now you can use your models,
  
.. code:: python

  from mydjangoapp.photos import models

  @app,route ('/django/hello')
  def django_hello (was):
    models.Photo.objects.create (user='Hans Roh', title = 'My Photo')  
    result = models.Photo.filter (user='hansroh').order_by ('-create_at')

You can use Django Query Set as SQL generator for Skitai's asynchronous query execution. But it has some limitations.

- just vaild only select query and prefetch_related () will be ignored
- effetive only to PostgreSQL and SQLite3 (but SQLite3 dose not support asynchronous execution, so it is practically meaningless)

.. code:: python

  from mydjangoapp.photos import models

  @app,route ('/hello')
  def django_hello (was):    
    query = models.Photo.objects.filter (topic=1).order_by ('title')  
    return was.jstream (was.sqlite3 ("@entity").execute (query).getwait ().data, 'data')  


Redirect Django Model Signals To Saddle Event
`````````````````````````````````````````````````

*Available on Python 3.5+*

Using with saddle's event, you can monitor the change of Django model and can do your jobs like updating cache.

This example show that if Django admin app is mounted to Skitai, whenever model is changed in Django admin, Saddle will receive signal and update cache data.

.. code:: python
  
  app = Saddle (__name__)  
  # activate wathcing model, and make accessible from was
  app.model_signal (modeler = "django")
  
  @app.on_broadcast ("model-changed:myapp.models.Photo")
  @app.mounted
  def model_changed (was, sender = None, *karg):
    from myapp.models import Photo
    
    # when app.mounted, sender is None
    if sender:
      # starts with 'x_', added by Saddle
      karg ['x_operation'] # one of C, U, D
      karg ['x_model_class'] # string name of model class like myapp.models.Photo
      
      # else Django's model signal args
      karg ['instance']
      karg ['update_fields']
    
    # creating cache object
    query = (sender or Photo).objects.all ().order_by ('created_at')
    was.backend (
      '@entity', 
      callback = lambda x, y = app: y.storage.set ('my-cache', x.data)
    ).execute (query)

For watching multiple models.

.. code:: python

  @app.on_broadcast ("model-changed:myapp.models.Photo", "model-changed:myapp.models.User")

If you would like listening all mounted Django model signals,
  
.. code:: python

  @app.on_broadcast ("model-changed")


Integrating With Skitai's Result Object Caching
`````````````````````````````````````````````````

*New in version 0.26.15*

.. code:: python

  app.model_signal (modeler = "django")
  
In backgound, app catch Django's model signal, and automatically was.setlu (your model class name like 'myapp.models.User'). Then you can just use was.getlu (your model class name).

.. code:: python

  @app.route ("/query")
  def query (was):
    req = was.backend (
      "@entity", 
      use_cache = was.getlu ("myapp.models.User")
    ).execute (...) 
    
    result = req.getwait ()
    result.cache (86400)
    return result.data

*Remember*, before using Django views and models, you should mount Django apps on Skitai first, and you should set all model keys using in apps.

.. code:: python

  skitai.addlu ('myapp.models.User', 'myapp.models.Photo')
  skitai.run ()
  

Logging and Traceback
------------------------

If Skitai run with -v option, app and exceptions are displayed at your console, else logged at files.

.. code:: python
  
  @app.route ("/")
  def sum ():  
    was.log ("called index", "info")    
    try:
      ...
    except:  
      was.log ("exception occured", "error")
      was.traceback ()
    was.log ("done index", "info")

Note inspite of you do not handle exception, all app exceptions will be logged automatically by Saddle. And it includes app importing and reloading exceptions.

- was.log (msg, category = "info")
- was.traceback (id = "") # id is used as fast searching log line for debug, if not given, id will be *Global transaction ID/Local transaction ID*


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
  
0.26 (May 2017)

- 0.26.18 (Jan 2018)
  
  - fix HTTP/2 remote flow control window
  - fix app.before_mount decorator exxcute point
  - add was.gentemp () for generating temp file name
  - add was.response.throw (), was.response.for_api() and was.response.traceback()
  - add @app.websocket_config (spec, timeout, onopen_func, onclose_func, encoding)
  - was.request.get_remote_addr considers X-Forwarded-For header value if exists
  - add param keep param to was.csrf_verify() 
  - add and chnaged app life cycle decorators:
    
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
  - add skitai.addlu (args, ...) that is equivalant to skitai.addlu (args, ...)
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
