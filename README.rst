At a Glance
=============

Skitai is a Python WSGI/HTTP Server for UNIX (Developing is possible on win32).

And simple to run:

Install,

.. code:: bash

  pip3 install -U skitai

Create and mount your app,

.. code:: python

  # myservice.py

  def app (env, start_response):
    start_response ("200 OK", [("Content-Type", "text/plain")])
    return 'Hello World'

  if __name__ == "__main__":
    import skitai

    skitai.mount ('/', app)
    skitai.mount ('/', '/var/www/statics')
    skitai.run (address = "127.0.0.1", port = 5000)

And run.

.. code:: bash

  python3 myservice.py

Your app will work for your thousands or miliions of customers.


Introduce
==============

Skitai is WSGI server and more than that.

Skitai/Atila_ has purpose for providing complete online runtime
environment for Python apps. You can make high concurrency with
async sockect works, threading, processing and subprocessing.
And you can use them with highly consistent manner.

Skitai handles requests with mainly asynchronous event loop and
threading pool and support websocket
within WSGI specification not with ASGI nor asyncio (It use asyncore).

- Websocket over HTTP 1.1
- HTTP 2.0 include h2c protocol
- HTTP 3.0 (beta)
- SSL/TLS
- Corequest (concurrent requests for upstreams and backgroud tasks)

.. _Atila: https://pypi.python.org/pypi/atila

.. contents:: Table of Contents


Installation
=========================

**Requirements**

Python 3.6+
PyPy3

**Installation**

Skitai and other core base dependent libraries is developing on
single milestone, install/upgrade all please. Otherwise it is
highly possible to meet some errors.

With pip

.. code-block:: bash

    pip3 install -U skitai

With git

.. code-block:: bash

    git clone https://gitlab.com/hansroh/skitai.git
    cd skitai
    pip3 install -e .

You have pla to use database engines or protocols which is supported by Skitai, you install them manually.

.. code-block:: bash

  pip3 install protobuf # for GRPC
  pip3 install redis
  pip3 install pymongo
  pip3 install psycopg2-binary
  # if you use pypy3 psycopg2cffi is better choice,
  pip3 install psycopg2cffi

*Note*

If you have `bson` related error, PyMongo has own `bson`
module that is incompatible with pypi `bson`. I cannot
exactly figure out this problem. If you really don't need
pypi bson, you can uninstall it:

.. code-block:: bash

  pip3 uninstall -y bson
  pip3 install -U --force pymongo

Or if you don't have plan using pymongo, uninstall it.

.. code-block:: bash

  pip3 uninstall -y pymongo


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
    skitai.mount ('/', 'app_v1/app:app'')

    import delune
    skitai.mount ('/', delune)
    skitai.mount ('/', (delune, 'app_v1')) # to specify app file
    skitai.mount ('/', (delune, 'app_v1:app')) # to specify app file and app name

  In case module object, the module should support skitai exporting spec.

- app_name: variable name of app
- pref: run time app config, pref will override app.config


Mount Django App
```````````````````

Basically same as other apps.

Let's assume your Django app project is '/mydjango' and
skitai app engine script is '/app.py'.

.. code:: python

  # and mount static dir used bt Django
  skitai.mount ("/static", "mydjango/static")

  with skitai.preference () as pref:
    import django

    pref.use_reloader = True
    pref.debug = True
    # finally mount django wsgi.py and project root path to append sys.path by path param.
    skitai.mount (
      "/",
      "mydjango/mydjango/wsgi:application",
      pref
    )
    skitai.mount (
      "/static/admin",
      os.path.join (os.path.dirname (django.__file__), "contrib", "admin", "static", "admin")
    )

Note that if app is smae location with django manage.py,
you need not path param.

Also note that if you set pref.use_reloader = True, it is possible
to replace Django development server (manage,py runserver), But it
will work on posix only, because Skitai reloads Django app by restarting
worker process, Win32 version doesn't support.

Run As Development Mode
``````````````````````````````

Skitai recommend to use runtime switch `--devel` when you develope.

It makes you app.debug = True, app.use_reloader = True
automatically. And without `--devel` option, it will
be applied as you specified.

The default values of these options are all `False`, then
if you do not specified, your app run safely and faster
in production mode (without `--devel` option).

You just run Skitai with `--devel` where you are in development.

.. code:: python

  python3 ./serve.py --devel

Also skitai.isdev () is detect wheather Skitai run with `--devel`.

You may not want to cache files when you are coding.

.. code:: python

  if not skitai.is_devel ():
      app.some_option = some_value_for_devel
      skitai.set_max_age ("/assets", 7200)

Cache control will be applied if production mode only.

Run As Silent Mode
``````````````````````````

Another related option `--silent` makes app.debug = False and
app.use_reloader = False forcely.

It will be useful, when you specified debug and use_reloader in
developing and make sure turn these options off in production mode.


Logging and Console Displaying For Developing/Debugging
----------------------------------------------------------

If you do not specify log file path, all logs will be
displayed in console, bu specifed all logs will be
written into file.

First of all, you should create log directory,

.. code:: bash

  sudo mkdir /var/log/skitai
  sudo chown ubuntu:ubuntu

Your request log file willl be placed to:
*/var/log/skitai/ubuntu/<script path hash>/request.log*.

.. code:: python

  skitai.mount ('/', app)
  skitai.enalbe_file_logging ()
  skitai.run (
    address = "0.0.0.0",
    port = 5000
  )

If you also want to view logs through console for spot developing,
you run app.py without option.

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

Skitai use short options -d, and long long options starts
with "---", then you SHOULD NOT use these options.
Also Skitai use satrt, restart, status, stop in args.
then these arguments are removed automatically.

.. code:: python

  skitai.add_option ('-D', '--dist', 'distribute mode, disable NodeJS proxing')
  skitai.add_option (None, '--db=DB_NAME', 'use specified database')
  ...
  active_db = skitai.options.get ('--db', 'testdb')
  is_dist = skitai.get_option ('-D', '--dist')

And if you use '--help', you can see like this:

.. code:: bash

  Usage: apiserve/serve.py [OPTION]... [COMMAND]...
  COMMAND can be one of [status|start|stop|restart|install|remove|update]

  Mandatory arguments to long options are mandatory for short options too.
    -d                      start as daemon, equivalant with `start` command
        ---profile          log for performance profiling
        ---gc               enable manual GC
        ---memtrack         show memory status
        --silent            disable auto reloading and debug output
        --devel             enable auto reloading and debug output
        --smtpda            run SMTPDA if not started
        --port=PORT_NUMBER  change port
    -D, --dist              distribute mode, disable NodeJS proxing
        --db=DB_NAME        use specified database

Note that all triple hypened options are reserved for Skitai.
DO NOT USE it.


Run with Threads Pool
------------------------

Skitai run defaultly multi-threading mode and number of threads are 4.
If you want to change number of threads for handling WSGI app:

.. code:: python

  skitai.mount ('/', app)
  skitai.run (
    threads = 8
  )


Run with Multiple Workers
---------------------------

*Available on posix only*

Skitai can run with multiple workers(processes)
internally using fork for socket sharing.

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

  ubuntu   25219     1    0 08:25 ?        00:00:00 skitai(myproject/app): master
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

This means if a worker's CPU usage is 90% for 20 seconds
continuously 3 times, Skitai try to kill this worker and
start a new worker.

If you do not want to use this, you just do not call
set_worker_critical_point () or set interval to zero (0).

But I strongly recommend use this setting especially
if you running Sktiai on single CPU processor machine
or like AWS t1.x limited computing instances.

Also this is for minimum protection against Skitai's
unexpected bugs.


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

    skitai.mount ('/', __file__)
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

Note: Above 3 files is in the same directory and then
both share templates directory. If you intend to seperate
from app_v1 and app_v2, you should seperate app with
directory like this:


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


Setting POST Body Size Limitation
------------------------------------

For setting 2 Gbytes limitation for POST body size,

.. code:: python

  import skitai

  skitai.set_max_upload_size (2 * 1024 * 1024 * 1024)


Setting Timeout
-----------------

Keep alive timeout means seconds gap of each requests.
For setting HTTP connection keep alive timeout,

.. code:: python

  skitai.set_keep_alive (2) # default = 30
  skitai.mount ('/', app)
  skitai.run ()

If you intend to use skitai as backend application server
behind reverse proxy server like Nginx, it is recommended
over 300.

Request timeout means seconds gap of data packet recv/sending events,

.. code:: python

  skitai.set_request_timeout (10) # default = 30
  skitai.mount ('/', app)
  skitai.run ()

Note that under massive traffic situation, meaning
of keep alive timeout become as same as request
timeout beacuse a clients requests are delayed by
network/HW capability unintensionally.

Anyway, these timeout values are higher, lower
response fail rate and longger response time. But
if response time is over 10 seconds, you might
consider loadbalancing things. Skitai's default
value 30 seconds is for lower failing rate under
extreme situation.

*New in version 0.26.15*

You can set connection timeout for your backends. Basue of Skitai's
ondemend polling feature, it is hard to know disconnected by server
side, then Skitai will forcley reconnect if over backend_keep_alive
after last interaction. Make sure your backends keep_alive setting
value is matched with this value.

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

Self Daemonizing
````````````````````

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


For automatic starting on system start, add a line
to /etc/rc.local file like this:

.. code:: bash

  su - ubuntu -c "/usr/bin/python3 /home/ubuntu/app.py -d"

  exit 0


Systemctl
`````````````````

.. code:: python

  # serve.py
  skitai.run (name = 'myservice')

To install service,

.. code:: bash

  python3 app.py --devel install # or update, you may need root permision

  sudo systemctl start myservice
  sudo systemctl stop myservice

  sudo python3 app.py --devel remove

The service is belong to current user.

If your app required root privileges for accessing lower ports
for HTTP3/QUIC protocol on serving.

.. code:: bash

  python3 app.py --devel --fallback-user ubuntu install


Adding Backend Server Alias
--------------------------------------

Backend server can be defined like this: (alias_type,
servers, role = "", source = "", ssl = False).

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
    - DJANGO: mount django database engine of settings.py
      if database engine is PostgreSQL or SQLite3

- server: single or server list, server form is
  [ username : password @ server_address : server_port
  / database_name weight ].
  if your username or password contains "@" characters,
  you should replace to '%40'
- role (optional): it is valid only when cluster_type is http or
  https for controlling API access
- source (optional): comma seperated ipv4/mask
- ssl (optional): use SSL connection or not, PROTO_HTTPS and
  PROTO_WSS use SSL defaultly

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

You can get certification from `Let's Encrypt` or where you want.

First of all, you make simple script for certbot challenge.

.. code:: bash

  mkdir myservice
  mkdir myservice/static
  cd myservice

And write serve.py,

.. code:: python

  #! /usr/bin/env python3

  import skitai

  skitai.mount ("/", "./static")
  skitai.run (port = 80, name = "my-service")

For using port 80, you need root permision,

.. code:: python

  chmod +x serve.py
  sudo ./serve.py

Now on another console,

.. code:: bash

  cd myservice
  sudo apt install certbot
  sudo certbot certonly --webroot \
    -w ./static \
    -d mydomain.com -d www.mydomain.com

Apply change to serve.py,

.. code:: python

  #! /usr/bin/env python3

  skitai.enable_ssl (
    '/etc/letsencrypt/live/mydomain.com/fullchain.pem',
    '/etc/letsencrypt/live/mydomain.com/privkey.pem'
  )
  # forward http -> https, www.mydomain.com -> mydomain.com
  skitai.enable_forward (80, 443, 'mydomain.com')

  skitai.mount ("/", "./static")
  skitai.run (port = 443, name = "my-service")

Becasue of you're using port 80, 443 you need root privileges.

.. code:: bash

  sudo ./serve.py

After binding port 80 and 443 and reading certifications, Skitai will drop root privileges and back to sudo user privileges.

FYI, for automating renew certification, start Skitai as daemon and add cron job,

.. code:: bash

  sudo ./serve.py -d

And add cron job with renew-hook,

.. code:: bash

  sudo crontab -e

  # add this line for trying renew twice a day, restart Skitai with user ubuntu privileges if renewed
  1 4,16 * * * /usr/bin/certbot renew --renew-hook="su - ubuntu -c 'sudo /PATH/myservice/serve.py restart'"

*Note*: If you just run with '/PATH/myservice/serve.py restart', server will run with nobody account privileges

.. _`Let's Encrypt`: https://letsencrypt.org


Self-Signed certification
````````````````````````````````````

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
In case Flask, it seems 'url_for' generate url by joining with env["SCRIPT_NAME"]
and route point, so it's not problem. Atila can handle obiously. But I don't know
other WSGI containers will work properly.


SMTP Delivery Agent
---------------------------------

*New in version 0.26*

e-Mail sending service is executed seperated system process not threading.
Every e-mail is temporary save to file system, e-Mail delivery process check
new mail and will send. So there's possibly some delay time.

You can send e-Mail in your app like this:

.. code:: python

    from skitai import was

    # email delivery service
    e = was.email (subject, snd, rcpt)
    e.set_smtp ("127.0.0.1:465", "username", "password", ssl = True)
    e.add_content ("Hello World<div><img src='cid:ID_A'></div>", "text/html")
    e.add_attachment (r"001.png", cid="ID_A")
    e.send ()

You can set default SMTP server and you can skip e.set_smtp (...) part.

.. code:: python

  skitai.set_smtp ("127.0.0.1:465", "username", "password", ssl = True)

For enabling this features,

.. code:: bash

  serve.py --smtpda

All e-mails are saved into /var/temp/skitai/smtpda.

This service will run as system-wide daemon service,
and will be not stopped even if app engine is stopped. For stopping it,

.. code:: bash

  skitai smtpda status
  skitai smtpda stop


Asccessing File Resources On Startup
--------------------------------------

Skitai's working directory is where the script call skitai.run ().
Even you run skitai at root directory,

.. code:: bash

  /app/example/app.py -d

Skitai will change working directory to /app/example on startup.

So your file resources exist within skitai run script, you can
access them by relative path,

.. code:: python

  monitor = skital.abspath ('package', 'monitor.py')

Also, you need absolute path on script,

.. code:: python

  skitai.getswd () # get skitai working directory


Enable Cache File System
------------------------------

If you make massive HTTP requests, you can cache contents by
HTTP headers - Cache-Control and Expires. these configures will
affect to 'was' request services, proxy and reverse proxy.

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

If max-age is only set to "/", applied to all files. But you
can specify it to any sub directories.

.. code:: python

  skitai.mount ('/', 'static')
  skitai.set_max_age ("/", 300)
  skitai.set_max_age ('/js', 0)
  skitai.set_max_age ('/images', 3600)
  skitai.run ()


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

This test client will start Skitai server on port 6000 with
app. app.py shoud have skitai.run ().

Note: Port that skitai.run (port = 5000) will be ignored, app.py
will be launched with port 6000 that specified by skitai.test_client
for avoiding exist app service.


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


If you run test server at another console window for watching
server error messages, give dry = True parameter.

.. code:: python

  @pytest.fixture (scope = "session")
  def cli ():
    c = skitai.test_client ("./app.py", 5000, dry = True)
    yield c
    c.stop ()

This test client will not start Skitai server but access to
port 5000 so you start server manually at another console,

.. code:: bash

  python3 app.py


Inter-Processes State Sharing
-------------------------------------------

*New in skitai version 0.26.18*

Skitai can run with multiple processes (a.k workers), It is
possible matters synchronizing state between workers.

'skitai.register_states ()'  can be used for allocating shared
memory for inter-process named state.

.. code:: python

  # __init__.py of your app

  import skitai

  def __setup__ (pref):
    skitai.register_states ("current-user", ...)

Then one process update object by setgs (name, value),
the others can be access it by getgs (name).

Note that value type is shoul be integer.

.. code:: python

  @app.before_request
  def before_request (was):
    was.setgs ("current-user", was.getgs ("current-user") + 1)

  @app.teardown_request
  def teardown_request (was):
    was.setgs ("current-user", was.getgs ("current-user") - 1)

For connecting to event bus,

.. code:: python

  skitai.register_states ("cluster.num-nodes", "region.somethig", ...)
  ...

  skitai.run ()

Then you can use these,

.. code:: python

  @app.route ("/nodes", method = ["POST", "DELETE"])
  def nodes (was, **nodinfos):
    ...
    was.setgs ("cluster.num-nodes", was.getgs ("cluster.num-nodes") + 1, **nodeinfos)

As a result,

- cluster.num-nodes state value has been increased
- "cluster.num-nodes" and  \*\*nodeinfos are broadcated
  to mounted all *Atila* apps.

A app has interest for this,

.. code:: python

  @app.on_broadcast ("cluster.num-nodes")
  def num_nodes_changed (num_nodes, **nodeinfos):
    ...

But this broadcasting is just within current workers.

All workers has interested in this event, You may add watching
routine at app.maintain.

.. code:: python

  app.config.MAINTAIN_INTERVAL = 60
  app.store ["num_nodes"] = 0

  @app.maintain
  def maintain_num_nodes (was, now):
    ..
    num_nodes = was.getgs ("cluster.num-nodes")
    if app.store ["num_nodes"] != num_nodes:
      app.store ["num_nodes"] = num_nodes
      app.broadcast ("cluster:num_nodes")

also was.setlu () and was.getlu () is very similar usage which
related to track resource updating. And it will be explained
`Corequest: Caching Result`_ chapter.

.. _`Corequest: Caching Result`: #caching-result


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
- username when HTTP auth: default '-', wrapped by double quotations
  if value available
- bearer token when HTTP bearer auth

- referer: default '-', wrapped by double quotations if value available
- user agent: default '-', wrapped by double quotations if value available
- x-forwared-for, real client ip before through proxy

- Skitai engine's worker ID like M(Master), W0, W1 (Worker
  #0, #1,... Posix only)
- number of active connections when logged, these connections
  include not only clients but your backend/upstream servers
- duration ms for request handling
- duration ms for transfering response data


Skitai with Nginx
---------------------------

If your service is relatvely simple and you may think using
Nginx is overkill, it is well enough with Skitai.

Below Nginx features (SSL, HTTP2, forwarding, proxy passing,
static file service etc) can be implemetented with Skitai alone.

But if you need some kind of gateway server which control multiple
upstreams and Skitai app engine instances, I strongly
recommend to use Nginx.

Here's some helpful sample works with Nginx.

.. code:: bash

  # upstreams with connection keep alive
  upstream backend {
    server 127.0.0.1:5000;
    keepalive 100;
  }

  server {
      listen 80;
      listen [::]:80;
      server_name www.oh-my-jeans.com;
      return 301 https://oh-my-jeans.com$request_uri;
  }

  server {
      listen 443;
      listen [::]:443;
      server_name www.oh-my-jeans.com;
      return 301 https://oh-my-jeans.com$request_uri;
  }

  server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name oh-my-jeans.com;

    ssl_certificate /etc/letsencrypt/live/www.oh-my-jeans.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/www.oh-my-jeans.com/privkey.pem;
    ssl_session_timeout 5m;
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    keepalive_timeout 30s;
    proxy_http_version 1.1;
    proxy_set_header X-NginX-Proxy true;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    add_header X-Backend "skitai app engine";
    proxy_set_header Host $http_host;

    location / {
      proxy_pass http://backend;
      client_max_body_size 2g;
    }

    location /websocket {
      proxy_pass http://backend;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "Upgrade";
      proxy_read_timeout 86400;
    }

    location /assets/ {
      alias /home/ubuntu/www/statics/assets;
      expires 300;
    }
  }


Run As API Gateway Server (Experimental)
-------------------------------------------------------------

Using Skitai's reverse proxy feature, it can be used as API Gateway Server.
All backend API servers can be mounted at gateway server with client
authentification and transaction ID logging feature.

.. code:: python

  def handle_claim (request_handler, request):
    claim = request.claim
    expires = claim.get ("expires", 0)
    if expires and expires < time.time ():
      return request_handler.continue_request (request)
    request_handler.continue_request (request, claim.get ("user"), claim.get ("roles"))

  @app.before_mount
  def before_mount (wac):
    wac.handler.set_auth_handler (handle_claim)

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

Gateway use only bearer tokens like OAuth2 and JWT(Json Web Token)
for authorization. And token issuance is at your own hands. But JWT creation,

.. code:: python

  from rs4 import jwt

  secret_key = b"8fa06210-e109-11e6-934f-001b216d6e71"
  token = jwt.gen_token (secret_key, {'user': 'Hans Roh', 'roles': ['user']}, "HS256")

Also Skitai create API Transaction ID for each API call, and this will be
explained in Skitai 'was' Service chapter.


Run as Win32 Service (Deprecated)
--------------------------------------------------

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


Self-Descriptive App
---------------------------

Skitai's one of philasophy is self-descriptive app. This means that
you once make your app, this app can be run without any configuration
or config files (at least, if you need own your resources/log files
directoring policy). Your app contains all configurations for not only
its own app but also Skitai. As a result, you can just install Skitai
with pip, and run your app.py immediately.

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

If your module need export APIs or web pages, you can
include app in your module for Skitai App Engine.

Let's assume your package name is 'unsub'.

Your app should be located at unsub/export/skitai/__export__.py

Then users uses your module can mount on skitai by like this,

.. code:: python

  import unsub

  with skitai.preference () as pref:
    pref.config.urlfile = skitai.abspath ('resources', 'urllist.txt')
    skitai.mount ("/v1", unsub, pref)
  skitai.run ()

If you want to specify filename like app_v1.py for version management,

.. code:: python

  skitai.mount ("/v1", (unsub, "app_v1:app"), pref)


If your app need bootstraping or capsulizing complicated initialize
process from simple user settings, write code to
unsub/export/skitai/__init__.py.

.. code:: python

  import skitai

  def __bootstrap__ (pref):
    with open (pref.config.urlfile, "r") as f:
      urllist = []
      while 1:
        line = f.readline ().strip ()
        if not line: break
        urllist.append (line.split ("  ", 4))
      pref.config.urllist = urllist

 *Important Note:* You should add zip_safe = False flag in your setup.py
 because Skitai could access your __export__ script and its sub modules.

.. code:: python

  setup (
    name = "mymodule",
    ...
    zip_safe = False
  )

Extending/Customizing Services
-----------------------------------------------

*New in version 0.28.15*

If you want to customize/extend services, create 'extends'
directory and mount it to pref.

.. code:: python

  # extends/apis.py
  def __mount__ (app):
    @app.permission_check_handler
    def permission_check_handler (was, perms):
      ...

    @app.route ("")
    def apis_index (was):
      return 'APIS'

.. code:: python

  # serve.py
  import unsub
  from extends import apis

  with skitai.preference () as pref:
    pref.mount ('/apis', apis)
    pref.config.urlfile = skitai.abspath ('resources', 'urllist.txt')
    skitai.mount ("/v1", unsub, pref)
  skitai.run ()

You can access it by /v1/apis.

If you want to mount another services from unpathed, you can specify
new path.

*Note:* This will change sys.path order. You SHOULD do
these on your last mount stage.

.. code:: python

  # serve.py
  import unsub

  with skitai.preference (path = '../my_service') as pref:
    from services import apis
    pref.mount ('/apis', apis)
    skitai.mount ("/v1", unsub, "app", pref)
  skitai.run ()



Examples
----------

Here're some implementations I made.

- `DeLune API Server`_
- `Haiku API Server`_
- `Tensorflow API Server`_

.. _`DeLune API Server`: https://pypi.python.org/pypi/delune
.. _`Tensorflow API Server`: https://pypi.python.org/pypi/tfserver
.. _`Haiku API Server`: https://pypi.python.org/pypi/haiku-lst


Protocols
=====================

HTTP/2.0
---------------------

*New in version 0.16*

Skiai supports HTPT2 both 'h2' protocl over encrypted TLS and 'h2c'
for clear text (But now Sep 2016, there is no browser supporting h2c protocol).

Push Promise
```````````````````````

Basically you have nothing to do for HTTP2. Client's browser will
handle it except `HTTP2 server push`_.

For using it, you just call was.push (uri) before return response
data. It will work only client browser support HTTP2 server push,
otherwise will be ignored.

.. code:: python

  from skitai import was

  @app.route ("/promise")
  def promise ():
    was.push ('/images/A.png')
    was.push ('/images/B.png')

    return was.response (
      "200 OK",
      (
        'Promise Sent<br><br>'
        '<img src="/images/A.png">'
        '<img src="/images/B.png">'
      )
    )

.. _`HTTP2 server push`: https://tools.ietf.org/html/rfc7540#section-8.2


HTTP/3.0 (Experimental)
-----------------------------------

*New in version 0.33*

**Python>=3.6 is required**

Skitai has been launched experimetnal HTTP/3 on QUIC with aioquic_.

*WARNING*: DO NOT use this for your production services. You must aware
that it is experimetal and unstable yet.


Requirements
````````````````````

.. code:: python

  apt install libssl-dev
  pip3 install aioquic


Configuring and Launching
``````````````````````````````````

HTTP3 can be run with https, you need a certification for it.

.. code:: python

  skitai.enable_ssl (
    '/etc/letsencrypt/live/mydomain.com/fullchain.pem',
    '/etc/letsencrypt/live/mydomain.com/privkey.pem'
  )
  skitai.mount ("/", "./static")
  skitai.run (name = "my-service", port = 443, quic = 4433)

And to avond port permission, you make port forwarding from UDP 443 to 4433.

.. code:: bash

  sudo iptables -A PREROUTING -t nat -i eth0 -p udp --dport 443 -j REDIRECT --to-port 4433

Also you open firewall UDP 443 not 4433.

*Note*: This MUST BE DONE, becasue:

- If QUIC port is not 443, it may be ignored by clients' browsers
- Secondary, Skitai will bind UDP port 443 per every clients for
  performance reason, and it need root privileges for running and
  it is not good idea. Also skitai doesn't allow keeping root
  privileges after started

This make both HTTP/2 and HTTP/3 services on TCP/UDP port 443.

And you need sudo for binding TCP port 443 and reading certification
on starting.

.. code:: bash

  sudo python3 ./serve.py

After started, Skitai will drop root privileges and fall back to
current user's.


For saving iptables settings,

.. code:: bash

  sudo apt install iptables-persistent

  sudo netfilter-persistent save
  sudo netfilter-persistent reload


Push Promise
`````````````````````

Pushing promise is just same as HTTP/2.0.


Testing HTTP/3
``````````````````````

You can test HTTP/3.0 with Chrome.

On Chrome address, type 'chrome://flags/' and find 'quic'. Then
enable 'Experimental QUIC protocol'.

You have to run Chrome with command line options,

.. code:: bash

   chrome.exe --quic-version=h3-25

At your browser's developer window, you can see protocol as
*h3-25* during you loading your web page and files.

.. _aioquic: https://github.com/aiortc/aioquic


HTML5 Websocket
---------------------------

*New in version 0.11*

The HTML5 WebSockets specification defines an API
that enables web pages to use the WebSockets protocol
for two-way communication with a remote host.

Skitai can be HTML5 websocket server and any WSGI containers can use it.

But I'm not sure my implemetation is right way, so it is
experimental and could be changable.


Using Websocket
````````````````````````

Use skitai.websocket decorator.

For example with Flask app,

.. code:: python

  import request

  @app.route ("/echo3")
  @skitai.websocket (60) # timeout
  def echo3 ():
    ws = request.environ ["websocket"]
    while 1:
      message = yield
      if not message:
        return #strop iterating
      yield "ECHO:" + message

I you want to send multiple messages,

.. code:: python

  yield ['OK', 'Task 1 started', 'Check later, please']
  # OR
  yield output_iterator ()


Proxying With Atila
```````````````````````````````

It follows WSGI specification as possible as can:

.. code:: python

  def start_response (environ, start_response):
    ...

Basically, Skitai calls this method on message arriving repeatly.
So it is quite ineeficient. If your WSGI framework give a websocket
handler object, it will have better performance but it is hard to expect.

Another option is that Sktai provide full usage spec with
routing, but I think it is not pretty.


So you can use Atila for websocket service (as websocket proxy)
beside your main app. and mount both app on Skitai.

With Atila app, you can use websocket more efficiently, and various options.

.. code:: python

  @app.route ("/websocket")
  @app.websocket (skitai.WS_CHANNEL | skitai.WS_SESSION, 60)
  def websocket (was):
    while 1:
      message = yield
      if not message:
        return #strop iterating
      yield "ECHO:" + message

For more about this see `Atila Websocket`_.

.. _`Atila Websocket`: https://pypi.org/project/atila/#more-about-websocket


WWW-Authenticate
```````````````````````````````

Some browsers do not support WWW-Authenticate on websocket
like Safari, then Skitai currently disables WWW-Authenticate
for websocket, so you should be careful for requiring secured messages.

Client Side
`````````````````````

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


Send Messages Through Websocket Directly
`````````````````````````````````````````````````````````

It needn't return message, but you can send directly
multiple messages through was.websocket,

.. code:: python

  @app.route ("/websocket/echo")
  @was.websocket ("message", 60)
  def echo ():
    message = request.args.get ("message")
    request.environ ["websocket"].send ("You said," + message)
    request.environ ["websocket"].send ("I said acknowledge")


Corequest
================

Skitai handle request connection with asynchronously,
also has threads and porcess ass workers.
So it works fine with synchronous apps and libraries.
You can use standard database client libraries or requests
module for API calls.

But Skitai's main event loop (using asyncore.loop) can be
used for not only client's requests else request to another
servers(API, Database engine...) asynchronously.

I think if I don't use this capabitities, it would be
wasting resources. Then, Skitai provide asynchronous
request methods for these operations.

*Corequest* is similar with Python coroutine object, but is
is not compatable at all.

- It is automatically started at creation, no need to call run ()
- All events are controlled by Skitai main event loop, not by asyncio
- It is eventually synchronous within current thread. It is desinged
  for working with multi-threading environment and synchronous code
  base so it has no differences with synchronous code base, just if
  you have to consider the most efficient point to call for waiting results
- It is not a framework nor a library. It is a Skitai native object
  has specified purpose and usage

Skitai provides some services related with corequests:

- Concurrent requests (like asyncio or gevent) to your
  API/Backend and Database engine servers
- Connection pooling
- Result caching

These features are just optional, but these might help
increase availability of your servers.

For using 'corequest', you need to import 'was':

.. code:: python

  from skitai import was

  @app.route ("/")
  def hello ():
    was.get ("http://...")


Basic
-------------------------

Task
```````````

Single corequest object.

API Call
~~~~~~~~~~~~~~~~

- was.get ()
- was.post ()
- was.put ()
- was.patch ()
- was.delete ()
- was.upload ()

Task will be created by just calling these methods.

.. code:: python

  task = was.get ('@myapi/v1/some-resources/100')

RPC Call
~~~~~~~~~~~~~~~~~

- was.xmlrpc ()
- was.grpc ()
- was.jsonrpc ()

Task will be created like this,

.. code:: python

  with was.xmlrpc ('@myrpc/rpc2') as stub:
    task = stub.some_method (arg1, arg2)

Database Call
~~~~~~~~~~~~~~~~~~

- was.db (): PostgreSQL, SQLite3, MongoDB and Redis calls
- was.transaction (): for RDBMS (PostgreSQL and SQLite3)

Task will be created like this,

.. code:: python

  # PostgreSQL and SQLite3
  with was.db('@mydb') as db:
    task = db.select ('my_table').execute ()

  # Redis or MongoDB
  with was.db('@mynosql') as db:
    task = db.find ({'city': 'New York'})

Thread/Process Call
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- was.Thread ()
- was.Process ()
- was.Subprocess ()

Task will be created like this,

.. code:: python

  task = was.Thread (my_func, arg1, arg2)

Methods of Task
~~~~~~~~~~~~~~~~~~~~~~~~~
Task has below core methods:

- dispatch (timeout)
- fetch (timeout)
- one (timeout): should be single lengthed object
- commit (timeout)
- returning (data)

Tasks
````````````````````

It is bundle of Tasks.

You can make it by wrapping.

.. code:: python

  tasks = was.Tasks ([task1, task2])
  result1, result2 = tasks.fetch ()

And it has also same methods as Task. But it can be accessed
by slicing or indexing for easy handling.

Mask
````````````````````

It is fake of Task(s).

You can make it by wrapping was.Mask (data) if you want to
use consistant methods as Task.

.. code:: python

  task = was.Mask (1)
  result = task.fetch () # 1

  tasks = was.Mask ([1, 2])
  result1, result2 = tasks.fetch () # 1, 2


Long Running Task(s)
````````````````````````````````

corequests is natively a kind of backgound jobs. So you can
 create these tasks and return yotur response - usally 202 Accepted.

More explicit way, creating tasks and immediately return 202 response.

.. code:: python

  return was.post ('@myapi/v1/some-resources').returning (Response ('202 Accepted'))

  return was.Thread (func, arg).returning (Response ('202 Accepted'))

Future(s)
`````````````````

*Available on Atila only*

On Atila_, you can hook the callback function with corequest objects.

- Task can be transformed into Future
- Tasks can be transformed into Futures

Future/Futures object can be returnable and it has the benefit
when your jobs are IO bound and long running time (but reasonably
close enough to real time). It returns current thread qucikly,
lazy respond when job is done.


Calling API
------------------------

.. code:: python

  @app.route (...)
  def request (was):
    req = was.get (url)
    resp = req.dispatch (timeout = 3)
    return resp.data

In fact, single request is just like synchronous task at least current thread.

.. code:: python

  @app.route (...)
  def request (was):
    req1 = was.get (url)
    req2 = was.post (url, {"user": "Hans Roh", "comment": "Hello"})
    respones1 = req1.dispatch (timeout = 3)
    response2 = req2.dispatch (timeout = 3)
    return [respones1.data, respones2.data]

Note that req1 and req2 will be executed concurrently.

dispath (timeout = [sec], cache = [sec]) returns response object.

.. code:: python

  req = was.get (url)
  rsponse = req.dispath (5) # timoute
  response.status # skitai.STA_NORMAL
  response.status_code # 200
  response.reason # OK
  response.get_header ("Content-Type") # application/json
  response.data # {"result": "ok"}

response.status is one of belows:

- STA_UNSENT
- STA_REQFAIL
- STA_TIMEOUT
- STA_NETERR
- STA_NORMAL

Note that STA_NORMAL just mean all requesting precess is
normally completed, NOT response is. Then you SHOULD check
before handle result data.

dispath_or_throw () will raise exception immediatly if
status !=  STA_NORMAL or status_code >= 300.

.. code:: python

  rsponse = req.dispath_or_throw (5) # timoute

If you want more short hand to result data,

.. code:: python

  result = req.fetch (5) # timoute and {"result": "ok"}

result = fetch (5) is equivalant with,

.. code:: python

  rsponse = req.dispath_or_throw (5) # timoute
  response = response.data

All supoorted request methods are:

HTTP/API related methods are,

- was.get ()
- was.delete ()
- was.post ()
- was.put ()
- was.patch ()
- was.upload ()
- was.options ()

Above request type is configured to json. This mean request
content type and response accept type is all 'application/json'.

If you want to change default value, use headers paramter for each request

.. code:: python

  data = {"Title": "...", "Content": "..."}
  headers = [
    ("Content-Type", "application/x-www-form-urlencoded"),
    ("Accept", "text/xml")
  ]
  req = was.post ("@delune/documents", data, headers = headers)


Tasks
-----------------------

Tasks is pack of corequests. It can handle multiple corequests as single one.

.. code:: python

  @app.route (...)
  def request (was):
    reqs = [
      was.get (url),
      was.post (url, {"user": "Hans Roh", "comment": "Hello"})
    ]
    a, b = was.Tasks (reqs, timeout = 3).fetch ()
    return was.API (a = a, b = b)

was.Tasks can be created from variadic parameters.

.. code:: python

  @app.route (...)
  def request (was):
    a, b = was.Tasks (
      was.get (url),
      was.post (url, {"user": "Hans Roh", "comment": "Hello"})
      timeout = 3
    ).fetch ()
    return was.API (a = a, b = b)


Alos can use keyword parameters and dict () method.

.. code:: python

  @app.route (...)
  def request (was):
    d = was.Tasks (
      a = was.get (url),
      b = was.post (url, {"user": "Hans Roh", "comment": "Hello"})
    ).dict ()
    # >> {'a': '<html>...', 'b': '<html>...'}
    return was.API (d)

dict () will not be include non keyword parametered requests.

.. code:: python

  @app.route (...)
  def request (was):
    d = was.Tasks (
      was.get (url),
      b = was.post (url, {"user": "Hans Roh", "comment": "Hello"})
    ).dict ()
    # >> {'b': '<html>...'}
    return was.API (d)


Tasks is iterable and slicable and returened rs is response
object (by dispatch ()). You SHOULD check rs.status and
status_code for validating response, or just use fetch ()
for raising error if invalid.

- Tasks (reqs, timeout = 10, \*\*meta)
- Tasks.add (corequest): append corequest or Task object
- Tasks.merge (corequest): append corequest or Task object,
  in case Tasks, it will be extracted from inner corequests
- Tasks.then (callabck): convert Tasks to Futures, available only for Atila app

- Tasks.dispatch (cache = None, cache_if = (200,), timeout = None)
- Tasks.wait (timeout = None)

- Tasks.commit (timeout = None)
- Tasks.fetch (cache = None, cache_if = (200,), timeout = None)
- Tasks.one (cache = None, cache_if = (200,), timeout = None)

- Tasks.meta: dictionary container for user data

*Note:* If you want to use full asynchronous manner,
you can consider Atila's Futures_, but it need to pay some costs.

.. _Futures: https://pypi.org/project/atila/#futures-response


Calling RPC
--------------------

.. code:: python

  @app.route (...)
  def request (was):
    with was.xmlrpc ("@myrpc") as stub:
      req = stub.get_version ("skitai")
      return req.fetch () # ["0.29"]

      # or single line
      return stub.get_version ("skitai").fetch ()

was.jsonrpc and was.grpc (Experimental) are also possible.

For gRPC example, calling to tfserver_ for predicting
something with tensorflow model.

.. code:: python

  from tfserver import cli

  @app.route (...)
  def predict_grpc (was):
    stub = was.grpc ("http://127.0.0.1:5000/tensorflow.serving.PredictionService")
    fftseq = getone ()
    request = cli.build_request ('model', 'predict', stuff = fftseq)
    req = stub.Predict (request, 10.0)
    resp = req.dispatch ()
    return cli.Response (resp.data).y

.. _aquests: https://pypi.python.org/pypi/aquests
.. _tfserver: https://pypi.python.org/pypi/tfserver


RDBMS Querying
------------------------------

*Important Note:* Async mode you cannot use transaction,
and auto commit will be applied.

PostgreSQL query at aquests, First uou alias your database
before running Skitai.

.. code:: python

  skitai.alias ("@mypg", skitai.DB_PGSQL, "user:pass@localhost/mydb")
  skitai.alias ("@mylite", skitai.DB_SQLITE3, "./sqlite3.db")
  skitai.run ()

Then,

.. code:: python

  @app.route (...)
  def query (was):
    with was.db ("@mypg") as db:
      req = db.excute ("SELECT city, t_high, t_low FROM weather;")
      resp = req.dispatch (timeout = 2)
      if resp.status != 200:
        raise HTTPError ("500 Server Error")
    for row in rows:
      row.city, row.t_high, row.t_low

For consistency handling response of API calls,
response.status_code will be set 200 if any error
does not occure, otherwise set 500.

Basically Skitai handle as same for all kind of external requests.

.. code:: python

  @app.route (...)
  def query (was):
    with was.db ("@mypg") as db:
      req = db.excute ("SELECT city, t_high, t_low FROM weather;")
      rows = req.fetch (2)
    for row in rows:
      row.city, row.t_high, row.t_low

If you needn't returned data and just wait for completing query,

.. code:: python

    db.execute ("INSERT INTO CITIES VALUES ('New York');").commit (timeout = 2)

If failed, exception will be raised.

In case database querying, you can use one () method.

.. code:: python

  @app.route (...)
  def query (was):
    with was.db ("@mypg") as db:
      hispet = db.excute ("SELECT ... FROM pets").one (timeout = 2)

If result record count is not 1 (zero or more than 1), raise HTTP 410 error.

With PostgreSQL you can also raise HTTP 409 using returning caluse.

.. code:: python

  @app.route (...)
  def query (was):
    with was.db ("@mypg") as db:
      hispet = db.excute ("INSERT INTO pets ... RETURNING id").one (timeout = 2)

If primary key or unique key is duplicated, psycopg2
raises IntegrityError then Skitai raise HTTP 409 Conflict error

*CAUTION*: DO NOT even think your statements will be
executed ordered sequencially.

.. code:: python

  @app.route (...)
  def query (was):
    with was.db ("@mypg") as db:
      reqs = [
        db.excute ("INSERT INTO weather (id, 'New York', 9, 25);"),
        db.excute ("SELECT city, t_high, t_low FROM weather order by id desc limit 1 ;")
      ]
      Tasks (reqs) [1].fetch () # No guarantee it is New York or something new

Execute and wait or use transaction.

.. code:: python

  @app.route (...)
  def query (was):
    with was.db ("@mypg") as db:
      db.excute ("INSERT INTO weather (id, 'New York', 9, 25);").commit ()
      latest = db.excute ("SELECT city, t_high, t_low FROM weather order by id desc limit 1 ;").fetch (2)
      # latest  is New York

Using Database Transaction
-------------------------------------------

If you want use asynchronous database transaction,
 you can use asynchronous drivers.

Also Skitai provide PostgreSQL connection with connection
pool. And SQLite connection without pool.

.. code:: python

  @app.route ("/")
  def index (was):
      with was.transaction ("@mypg") as tx:
          tx.execute ('INSERT ...')
          tx.execute ('UPDATE ...')
          tx.execute ('SELECT ...')
          tx.fetch () # equivlant to fetchall () but list of dict type
          tx.commit ()

With context manager, connection will return back to the pool
automatically else you SHOULD call tx.putback () manually.

In transaction mode, standard DBAPI - rollback (), fetchall (),
fetchone () and fetchmany () are also possible but caching is not.

was.transaction has second paramter 'auto_putback'. If it is False,
transaction object does not return to the pool automatically.

.. code:: python

  # models.py
  from skitai import was

  def update (...):
      with was.transaction ("@mypg", False) as tx:
          tx.execute ('INSERT ...')
          tx.execute ('UPDATE ...')
          tx.execute ('SELECT ...')
          return tx

          tx.fetch () # equivlant to fetchall () but list of dict type

  # app.py
  import models

  @app.route (...)
  def update (was):
    tx = models.update (...)
    rows = tx.fetch ()
    tx.commit ()

Note that you MUST call commit/rollback finally, if not
connection pool will be exhausted very soon and entire threads
will be blocked.


Using SQLPhile for Querying
----------------------------------------------

Actullay, was.db and was.transaction are fully intergrated with SQLPhile_.

You can write with raw SQL,

.. code:: python

  with was.db ("@mydb") as db:
    rows = db.execute (
      "SELECT a.id, b.name, c.phone "
      "FROM user a, profile b, contact c "
      "WHERE b.name like '%{name}%'"
      "ORDER BY a.id desc"
      "LIMIT {limit}".format (name = name, limit = limit)
    ).fetch ()

But also can use SQLPhile_ style,

.. code:: python

  with was.db ("@mydb") as db:
    rows = (db.get ("a.id, b.name, c.phone")
            .select ("user a, profile b, contact c")
            .filter (b__name__contains = name)
            .order_by ("-a.id") [:limit]
            .execute ().fetch ())

It may be not very helpful because of my laziness of documentation,
however SQLPhile_ can provide some other benefits using SQL I
recommend read it instantly.

.. _SQLPhile: https://pypi.org/project/sqlphile/

NoSQL Querying
------------------------------------

.. code:: python

  skitai.alias ("@mymongo", skitai.DB_MONGODB, "localhost/mycollection")
  skitai.alias ("@myredis", skitai.DB_REDIS, "localhost/0")
  skitai.run ()

Then,

.. code:: python

  @app.route (...)
  def query (was):
    with was.db ("@mymongo") as db:
      documents = db.find ({'city': 'New York'}).fetch (2)

    with was.db ("@myredis") as db:
      db.set('foo', 'bar').wait ()
      db.get('foo').fetch () # bar


Request As Many You Need
------------------------------------------------

For getting concurrent tasks advantages, you request at
 once as many as possible.

.. code:: python

  @app.route (...)
  def query (was):
    reqs = was.post ("@pypi/upload...", {data: ...})
    reqs = was.get ("@pypi/somethong..."})
    with was.db ("@mypg") as db:
      reqs.append (db.excute ("SELECT ..."))
      reqs.append (db.excute ("SELECT ..."))

    with was.jsonrpc ("@pypi/pypi") as stub:
      reqs.append (stub.get_version ("skitai"))
      reqs.append (stub.get_version ("atila"))

    contents = []
    for rs in Tasks (reqs, 3):
      if rs.status_code != 200:
        contents.append ("Error")
      else:
        contents.append (str (rs.data))
    return contents


Intermezzo
-------------------

For creating corequest object,

- HTTP based request: was.get (alias), .post (alias), ....
- Database request: as.db (alias).execute (...), .find (),
  set (), ... other MongoDB and Redis methods
- Tasks: bundle of corequests

Corequest object has main 5 methods.

- dispatch (): it returns Result object contains data
  (or text/content) and request status information
- wait (): it returns Result object contains request status information
- fetch (): it returns records list. if request failed raise exception
- one (): it returns one record if query result length is exactly
  one otherwise raise 410 or 409 HTTP error. if request failed
  raise exception
- commit (): it wait finishing non-select query, if request failed
  raise exception

Result object is mainly used for checking status and handling error
to individual corequest, and Result object also has fetch (), one ()
and commit ().

Please DO remember. If ou call dispatch, fetch, ... to corequest
object, it immediatly act as synchronous task. But already created
another corequests are still has concurrency.


Load-Balancing
---------------------------

Skitai support load-balancing requests.

If server members are pre defined, skitai choose one
automatically per each request supporting *fail-over*.

Then let's request XMLRPC result to one of mysearch members.

.. code:: python

  @app.route ("/search")
  def search (was, keyword = "Mozart"):
    with was.jsonrpc.lb ("@mysearch/rpc2") as stub:
      s = stub.search (keyword)
      results = s.dispatch (timeout = 5)
      return result.data

      # or short hand
      return stub.search (keyword).fetch (5)

  if __name__ == "__main__":
    import skitai

    skitai.alias (
      '@mysearch',
       skitai.PROTO_HTTPS,
       ["s1.myserver.com", "s2.myserver.com"]
    )
    skitia.mount ("/", app)
    skitai.run ()

It just small change from was.jsonrpc () to was.jsonrpc.lb ()

*Note:* If @mysearch member is only one, was.get.lb ("@mydb")
is equal to was.get ("@mydb").

*Note2:* You can mount cluster @mysearch to specific path as
proxypass like this:

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

It can be accessed from http://127.0.0.1:5000/search, and handled as
load-balanced proxypass. And it will be remapped to http://s1.myserver.com/.

If you mount like this,

.. code:: bash

  skitia.mount ("/search", '@mysearch/search')

It can be accessed from same URL, but it will be remapped
to http://s1.myserver.com/search.


This sample is to show loadbalanced querying database.
Add mydb members to config file.

.. code:: python

  @app.route ("/query")
  def query (was, keyword):
    with was.db.lb ("@mydb") as dbo:
      req = dbo.execute ("SELECT * FROM CITIES;")
      result = req.dispatch (timeout = 2)

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
---------------------------------------

Basically same with load_balancing except Skitai requests to
all members per each request.

.. code:: python

  @app.route ("/search")
  def search (was, keyword = "Mozart"):
    with was.rpc.map ("@mysearch/rpc2") as stub:
      req = stub.search (keyword)
      results = req.dispatch (timeout = 2)

    all_results = []
    for result in results:
       all_results.extend (result.data)
    return all_results

There are 2 changes:

1. from was.rpc.lb () to was.rpc.map ()
2. results is iterable

You can use Dataabse, API calls same way.


Caching Result
---------------------------------------

By default, all HTTP requests keep server's cache policy given by HTTP
response header (Cache-Control, Expire etc). But you can control cache
as your own terms including even database query results.

Every results returned by dispatch() can cache.

.. code:: python

  s = was.rpc.lb ("@mysearch/rpc2").getinfo ()
  result = s.dispatch (60, timeout = 2) # cache seconds
  result.data

  s = was.rpc.map ("@mysearch/rpc2").getinfo ()
  results = s.dispatch (60, timeout = 2)

Cahing when just only Although code == 200 alredy implies status == STA_NORMAL.


*New in version 0.15.28*

You can control number of caches by your system memory before running app.

.. code:: python

  skitai.set_max_rcache (300)
  skitai.mount ('/', app)
  skitai.run ()

For expiring cached result by updating new data:

.. code:: python

  refreshed = False
  if was.request.method == "POST":
    ...
    refreshed = True

  s = was.rpc.lb (
    "@mysearch/rpc2",
    use_cache = not refreshed and True or False
  ).getinfo ()
  result = s.fetch (2, 60)

If you want cache for another status_code,

.. code:: python

  s = was.rpc.lb (
    "@mysearch/rpc2",
    use_cache = not refreshed and True or False
  ).getinfo ()
  result = s.dispatch (60, (200, 201), timeout = 2)


More About Cache Control: Model Synchronized Cache
```````````````````````````````````````````````````

*New in version 0.26.15*

You can efficient cache with explicit model mutation time.

- when your model is changed, call was.setlu ("model-state-name")
- when query your model, add parameter - was.getlu ("model-state-name"),
  for deciding if use cache or not

*Note* that it is useful only if your model make regular and controlled
mutation by single or a few producer (any of computer, machine or human).
Otherwise you could consider NoSQL things for your cache system, and
Skitai corequest support MongoDB and Redis.


Corequest's `use_cache` parameter value can be True, False or last
updated time of base object. If last updated is greater than cached
time, cache will be expired immediately and begin new query/request.

You can integrate your models changing and cache control.

First of all, you should set all cache control keys to Skitai
for sharing model state beetween worker processes.

.. code:: python

  # __init__.py in your app root

  import skitai

  def __setup__ (pref):
    skitai.register_cache_keys ('tables.users', 'table.photos')

Note: skitai.register_cache_keys shoud be placed on your 'serve.py'
or '\_\_init\_\_.py'.

These key names are might be related your database model names nor table names. In general cases, key names are fine if you easy to recognize.

These key names are not mutable and you cannot add new key after calling skitai.run ().

Also it can be used as decorator for clarency.

.. code:: python

  # __init__.py in your app root

  import skitai

  def __setup__ (pref):
    skitai.register_cache_keys ('tables.users')


Then you can use setlu () and getlu (),

.. code:: python

  app = Atila (__name__)

  @app.route ("/update")
  def update (was):
    # update users tabale
    was.db ('@mydb').execute (...)
    # update last update time by key string
    was.setlu ('tables.users')

  @app.route ("/query1")
  def query (was):
    # determine if use cache or not by last update information 'users'
    was.db ('@mydb', use_cache = was.getlu ('tables.users')).execute (...)

It makes helping to reduce the needs for building or managing caches.
And the values by setlu() are synchronized between Skitai workers by
multiprocessing.Array.

If your query related with multiple models,

.. code:: python

  use_cache = was.getlu ("myapp.models.User", "myapp.models.Photo")

was.getlu () returns most recent update time stamp of given models.


For comprehensive, you can use 'rm_cache' argument.

.. code:: python

  app = Atila (__name__)

  @app.route ("/update")
  def update (was):
    # update users tabale
    was.db ('@mydb', rm_cache = 'tables.users').execute (...)

  @app.route ("/query")
  def query1 (was):
    # determine if use cache or not by last update information 'users'
    was.db ('@mydb', use_cache = 'tables.users').execute (...)

For advanced use, cache keys can be segmentated,

.. code:: python

  skitai.register_cache_keys (
    *['category-{}'.format (category_code) for category_code in range (10)]
  )


.. code:: python

  app = Atila (__name__)

  @app.route ("/update")
  def update (was, category_code):
    # update article tabale
    was.db ('@mydb', rm_cache = 'category-{}'.format (category_code)).execute (...)

  @app.route ("/query1")
  def query1 (was, category_code):
    # determine if use cache or not by last update information 'article'
    was.db ('@mydb', use_cache = 'category-{}'.format (category_code)).execute (...)


*Available on Python 3.5+*

Also was.setlu () emits 'model-changed' events. You can handle
event if you need. But this event system only available on
Atila_ middle-ware.

.. code:: python

  app = Atila (__name__)

  @app.route ("/update")
  def update (was):
    # update users tabale
    was.db ('@mydb').execute (...)
    # update last update time by key string
    was.setlu ('tables.users', something...)

  @app.on_broadcast ("model-changed:tables.users")
  def on_broadcast (was, *args, **kargs):
    # your code

Note: if @app.on_broadcast is located in mount function at
services directory, even app.use_reloader is True, it is not
applied to app when component file is changed. In this case
you should manually reload app by resaving app file.

Note2: Cache keys limitations is 256 (including 'states').


Corequest Based Model
---------------------------------------------

Here's an model example with RDBMS.


Alias Your Database
````````````````````````````

First of all, alias your database to Skitai.

.. code:: python

  # serve.py
  ...
  skitai.alias ("@blog", skitai.DB_PGSQL, "postgres:password@localhost/blog")
  ...
  skitai.run (port = 5000)


Create Model Classes
````````````````````````````````````

I think all public model methods SHOULD return only two things:

- corequest objects
- None

And **DO NOT USE** request specific objects, Skitai do not
ensure these objects are same in current request flow.

- was.env
- was.app
- was.request
- was.response
- was.session
- was.cookie

But you can still use corequest related nethods and other
utility methods.


.. code:: python

  # services/models.py

  from skitai import was
  import skitai
  from sqlphile import Q
  from datetime import datetime

  class BlogPost:
    EXCLUDES = Q (share = 'test')

    @classmethod
    def search (cls, keyword = None, period = None, offset = 0, limit = 10, fields = "*"):
        with was.db ("@blog") as db:
            stem = (db.select ("blogpost")
                     .get (fields)
                     .exclude (cls.EXCLUDES)
                     .filter (posted_at__between = period)
                     .filter (Q (title__contains = keyword) | Q (content__contains = keyword)))

            reqs = [
                stem.branch ().get ("count (*) as total").execute (),
                (stem.branch ()
                    .order_by ("-posted_at").offset (offset).limit (limit)
                    .execute ())
            ]
            return was.Tasks (reqs)

    @classmethod
    def get (cls, id, fields = "*"):
        with was.db ("@blog") as db:
            return (db.select ("blogpost")
                        .get (fields)
                        .filter (id = id).execute ())

    @classmethod
    def delete (cls, id):
        # example for transaction deletion
        was.setlu (STATE_POST)
        with was.transaction ("@blog") as db:
            (db.delete ("blogcomment")
                        .filter (post_id = id).execute ())
            (db.delete ("blogpost")
                        .filter (id = id).execute ())
            db.commit ()

    @classmethod
    def add (cls, post):
        was.setlu (STATE_POST)
        with was.db ("@blog") as db:
            return (db.insert ("blogpost")
                        .data (post)
                        .returning ("id").execute ())

    @classmethod
    def update (cls, id, post):
        was.setlu (STATE_POST)
        post ["updated_at"] = datetime.now ()
        with was.db ("@blog") as db:
            return (db.update ("blogpost")
                        .data (post)
                        .filter (id = id).execute ())

    @classmethod
    def get_comments (cls, id, offset = 0, limit = 10):
        with was.db ("@blog") as db:
            return (db.select ("blogcomment")
                      .filter (post_id = id)
                      .offset (offset).limit (limit)
                      .execute ())

    @classmethod
    def get_stat (cls, dateunit = 'year'):
        with was.db ("@blog") as db:
            return (db.select ("blog")
                    .get (f"date_part('{dateunit}', created_at) as year, count (*) as cnt")
                    .group_by ("year")
                    .execute ())


Using Models
```````````````````````````

Finally, you can use this models.py.

.. code:: python

  # services/blog.py
  from . models import BlogPost

  @app.route ("/posts/", methods = ["GET", "POST"])
  def posts (was, offset = 0, limit = 10, **payload):
    if was.request.method == "GET":
      stat, posts = BlogPost.search (offset = int (offset), limit = int (limit)).fetch ()
      return was.API (posts = posts, total = stat [0].total)

    new_post = BlogPost.add (payload).one ()
    return was.API ("201 Created", id = new_post.id)

  @app.route ("/posts/<int:id>", methods = ["GET", "PATCH", "DELETE", "OPTIONS"])
  def post (was, id, num_comments = 0):
    if was.request.method == "GET":
      comments_ = BlogPost.get_comments (id, 0, int (num_comments))
      post = BlogPost.get (id).one ()
      post.comments = comments_.fetch ()
      return was.API (post = post)

    if was.request.method == "DELETE":
      BlogPost.delete (id)
      return was.API ("204 No Content")
    ...

  @app.route ("/posts/int:id>/comments", methods = ["GET", "PATCH", "DELETE", "OPTIONS"])
  def comments (was, id, offset = 0, limit = 10):
    if was.request.method == "GET":
      comments = BlogPost.get_comments (id, int (offset), int (limit)).fetch ()
      return was.API (comments = comments)
    ...


Conclusion
`````````````````````````

Above example pattern is just one of my implemetation with async models.

It can be extended and changed into NoSQL or even RESTful/RPC
with any Skitai corequest object which has same 5 methods - dispatch,
wait, fetch, one and commit.


Background Tasks
---------------------------------

Skitai integrated async/sync concurrents. They have also very
same usage and methods like fetch, one, dispatch etc.

Task(s) object is natively async corequests. It creates backgorund
async jobs and can be responded immediately.

.. code:: python

  @app.route ('...')
  def foo ():
    req = was.get ("@myupstream/something")
    return  req.returning (
      Response ('', 202, headers = {'Content-Location': "..."})
    )

Tasks is also available,

.. code:: python

  @app.route ('...')
  def foo ():
    reqs = [
      was.get ("@myupstream/something"),
      was.post ("@myupstream/something", {})
    ]
    return was.Tasks (reqs).returning (
      Response ('', 202, headers = {'Content-Location': "..."})
    )

*Note*: With Atila_, you can add callback for late response.

Process / Thread is very same as Task.

Skitai will create thread/process pool as you use it at once.
If you do't use this, pool will not be created for resource
saving. Pool size is your number of CPUs.

You can just use multi processing with pool instantly.

.. code:: python

  def side_job (a, b):
    ...

  @app.route ('...')
  def foo ():
    ps = was.Process (job2, 1000, -1000)
    ...
    result = ps.fetch () # wait for finishing
    return Response (result, 200, headers = {'Content-Type': "application/vnd-..."})

Also you can create async jobs for long run process.

.. code:: python

  @app.route ('...')
  def foo ():
    return was.Process (job2, 1000, -1000).returning (
      Response ('', 202, headers = {'Content-Location': "..."})
    )

was.Thread () and was.Subprocess () are also available.

- was.Thread (target, \*args, \*\*kargs):
  return wrapper of concurrent.futures.Future
- was.Process (target, \*args, \*\*kargs):
  return wrapper of concurrent.futures.Future
- was.Subprocess (command, timeout = 300):
  return wrapper of subprocess.Popen

*Note*: With Atila_, you can add callback for late response.


Miscellaneous
==============================

API Transaction ID
------------------------------------

*New in version 0.21*

For tracing REST API call, Skitai use global/local transaction IDs.

If a client call a API first, global transaction ID (gtxnid) is
assigned automatically like 'GTID-C4676-R67' and local transaction
ID (ltxnid) is '1000'.

You call was.get (), was.post () or etc, both IDs will be forwarded
via HTTP request header. Most important thinng is that gtxnid is never
changed by client call, but ltxnid will be changed per API call.

when client calls gateway API or HTML, ltxnid is 1000. And if it
calls APIs internally, ltxnid will increase to 2001, 2002. If
ltxnid 2001 API calls internal sub API, ltxnid will increase to
3002, and ltxnid 2002 to 3003. Briefly 1st digit is call depth
and rest digits are sequence of API calls.

This IDs is logged to Skitai request log file like this.

.. code:: bash

  2016.12.30 18:05:06 [info] 127.0.0.1:1778 127.0.0.1:5000 GET / \
  HTTP/1.1 200 0 32970 \
  GTID-C3-R8 1000 - - \
  "Mozilla/5.0 (Windows NT 6.1;) Gecko/20100101 Firefox/50.0" \
  4ms 3ms

Focus 3rd line above log message. Then you can trace a series
of API calls from each Skitai instance's log files for finding
some kind of problems.

In next chapters' features of 'was' are only available for
*Atila WSGI container*. So if you have no plan to use Atila, just skip.


Utility Methods of 'was'
-------------------------------------

This chapter's 'was' services are also avaliable for all WSGI middelwares.

- was.status () # HTML formatted status information
- was.get_lock (name = "__main__") # getting process lock
- was.gentemp () # return temp file name with full path
- was.restart () # Restart Skitai App Engine Server,
  but this only works when processes is 1 else just
  applied to current worker process.
- was.shutdown () # Shutdown Skitai App Engine Server,
  but this only works when processes is 1 else just applied
  to current worker process.


Links
======

- `GitLab Repository`_
- Bug Report: `GitLab issues`_

.. _`GitLab Repository`: https://gitlab.com/hansroh/skitai
.. _`GitLab issues`: https://gitlab.com/hansroh/skitai/issues
.. _`Skitai WSGI App Engine Daemon`: https://pypi.python.org/pypi/skitaid


Change Log
============

- 0.35 (Feb 2020)

  - use loky_ for avoiding processpool deadlock
  - remove ujson-ia dependency, it may have memory leak
  - reengineering threading locks for asynconnect, http_channels
    and http2/3 handlers
  - from version 0.35.2, required aioquic>=0.9 if you need HTTP/3
  - add dict () method to was.Tasks
  - add 'filter' argument to was.Thread, Process and Subprocess
  - change dependency: ujosn => ujson-ia
  - add app.config.PRETTY_JSON (default is False, 2 spaces indented JSON format)
  - drop support Python 3.5 officially
  - catch SIGHUP for reloading worker process
  - add skitai command: install, remove and update for systemctl script
  - add sktai.get_option (\*options)
  - make aioquic installation optional
  - update Django reloader for 2.xx
  - fix corequest cache expiring
  - support h3-25, h3-26
  - add skitai.set_max_was_clones_per_thread (val)
  - fix corequest cache
  - deprecate corequest.Task(s) keyword arguments, instead add meta
    argument
  - enable Range header to WSGI content

- 0.34 (Jan 2020)

  - fix proxy and proxypass for PATCH method
  - add `--devel` and `--silent` runtime options
  - remove `--production` runtime options
  - lower version comaptible: change app bootstraping
    function name: bootstrap -> \_\_setup\_\_

- 0.32 (Oct 2019)

  - initiate HTTP3+QUIC, you can test HTTP/3 with Chrome Canary

- 0.31 (Sep 2019)

  - change handling command line options, required rs4>=0.2.5.0
  - add skitai.set_smtp ()
  - remove protobuf, redis, pymongo and psycopg2 from requirements,
    if you need these, install them maually
  - skitai.preference () can be used with context
  - fix http/2 response delaying when body is not exist
  - skitai.enable_forward () can forward to single domain
  - add dropping root privileges when Skitai run with sudo for using
    under 1024 ports etc.
  - refix: master process does not drop root privileges for clean resources
  - fix reloading for file mounted apps
  - confirmed to work on PyPy3

- 0.30 (Sep 2019)

  - skitai.websocket spec changed, lower version compatable

- 0.29 (Aug 2019)

  - add was.Subprocess
  - add handlers for Range, If-Range, If-Unmodified-Since, If-Match headers
  - asyncore and asynchat are vendored as rs4.asyncore and chat,
    because they will be exsanguinated from standard Python library.
    Mr. Rossum has been listed up on my mortal enemy list
  - deprecated: was.Future and was.Futures, it doesn't need. for
    using returning (), use corequest.returning () and was.Tasks.returning ()
  - new corequest.pth package
  - over 100 unit tests

- 0.28 (Feb 2019)

  - fix auto reloading bug in case multiple apps are mounted
  - add was.Thread () and was.Process ()
  - add @skitai.states () decorator
  - rename skitai.deflu () => skitai.register_states ()
  - add corequest object explaination and corequest based model example
  - drop SQLAlchemy query statement object
  - fix https proxypass, and add proxypass remapping
  - add was.transaction ()
  - update psycopg2 connection parameter: async => async\_
    for Py3.7 compatablity
  - replace from data_or_thow (), one_or_throw () to fetch (), one ()
  - fix HTTP2 server push and add was.push ()
  - getwait () and getswait () are integrated into dispatch ()
  - add data_or_throw () and one_or_throw ()
  - was.promise has been deprecated, use was.futures: see Atila documentation
  - reinstate gc.collect () schedule
  - fix GTXID
  - fix app reloader
  - remove gc.collect () schedule
  - support SQLAlchemy query statement object
  - removed sugar methods: was.getjson, getxml, postjson, ...,
    instead use headers parameter or app.config.default_request_type
  - skitai.win32service has been moved to rs4.psutil.win32service
  - improve 'was' magic method search speed
  - seperate skitai.saddle into atila

- 0.27.6 (Jan 2019)

  - rename directory decorative to services
  - change from skital.saddle.contrib.decorative to
    skital.saddle.contrib.services

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
  - rename @app.preworks -> @app.run_before and @app.postworks
    ->  @app.run_after
  - add @app.bearer_handler
  - add was.mkjwt and was.dejwt
  - add was.timestamp amd was.uniqid
  - renamed was.token -> was.mktoken
  - renamed api -> API, for_api -> Fault
  - skitai.use_django_models has been deprecated, use skitai.alias
  - functions are integrated skitai.mount_django into skitai.mount,
    skitai.alias_django into skitai.alias
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
  - add was.response.throw (), was.response.for_api()
    and was.response.traceback()
  - add @app.websocket_config (spec, timeout, onopen_func,
    onclose_func, encoding)
  - was.request.get_remote_addr considers X-Forwarded-For header
    value if exists
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
  - add some methods to was.djnago: login (), logout (), authenticate ()
    and update_session_auth_hash ()
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
  - change params of use_django_models: (settings_path, alias),
    skitai.mount_django (point, wsgi_path, pref = pref (True),
    dbalias = None, host = "default")

- 0.26.16 (Oct 2017)

  - add app.sqlmaps
  - add use_django_models (settings_path), skitai.mount_django
    (point, wsgi_path, pref = pref (True), host = "default")
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
  - add skitai.set_proxy_keep_alive (channel = 60, tunnel = 600)
    and change default proxy keep alive to same values
  - increase https tunnel keep alive timeout to 600 sec.
  - fix broad event bus
  - add getjson, deletejson, this request automatically add header
    'Accept: application/json'
  - change default request content-type from json to form data,
    if you post/put json data, you should change postjson/putjson
  - add skitai.trackers (args,...) that is equivalant to skitai.lukeys ([args])
  - fix mounting module
  - app.storage had been remove officially, I cannot find any usage. but unoficially
    it will be remains by some day
  - add skitai.lukeys () and fix inconsistency of was.setlu
    & was.getlu between multi workers
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
  - change default mime-type from text/plain to
    application/octet-stream in response header
  - HTTP response optimized

- 0.26.10

  - start making pytest scripts
  - add was-wide broadcast event bus: @app.listen (event),
    was.broadcast (event, args...) and @was.broadcast_after (event)
  - add app-wide event bus: @app.on (event), was.emit (event, args...)
    and @was.emit_after (event)
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
  - websocket design spec, WEBSOCKET_DEDICATE_THREADSAFE has been
    removed and WEBSOCKET_THREADSAFE is added
  - fix websocket, http2, https proxy tunnel timeout, related
    set_network_timeout () is recently added

- 0.26.4.1: add set_network_timeout (timoutout = 30) and change
  default keep alive timeout from 2 to 30
- 0.26.4: fix incomplete sending when resuested with connection: close header
- 0.26.3.7: enforce response to HTTP version 1.1 for 1.0 CONNECT
  with 1.0 request
- 0.26.3.5: revert multiworkers
- 0.26.3.2: fix multiworkers
- 0.26.3.1: update making for self-signing certification
- 0.26.3: add skitai.enable_forward
- 0.26.2.1: remove was.promise.render_all (), change method name
  from was.promise.push () to send ()
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
- integrated with skitaid package, single app file can contain
  all configure options
- level down developement status to alpha
- fix sqlite3 closing

0.25 (Feb 2017)

- 0.25.7: fix fancy url, non content-type header post/put request
- 0.25.6: add Chameleon_ template engine
- 0.25.5: app.jinja_overlay ()'s default args become jinja2 default
- 0.25.4.8: fix proxy retrying
- 0.25.4 license changed from BSD to MIT, fix websocket init at single thread
- 0.25.3 handler of promise args spec changed, class name is
  changed from AsyncResponse to Promise
- 0.25.2 fix promise exception handling, promise can send streaming chunk data
- 0.25.1 change app.jinja_overlay () default values and number
  of args, remove raw line statement
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
- WEBSOCKET_MULTICAST deprecated, and new WEBSOCKET_GROUPCHAT
  does not create new thread any more

0.23 (Jan 2017)

- ready_producer_fifo only activated when proxy or reverse
  proxy is enabled, default deque will be used
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
- 0.21.3 - add JWT (JSON Web Token) handler, see
  `Skitai WSGI App Engine Daemon`_
- 0.21.2 - applied global/local-transaction-ID to app
  logging: was.log (msg, logtype), was.traceback ()
- 0.21 - change request log format, add global/local-transaction-ID
  to log file for backtrace

0.20 (Dec 2016)

- 0.20.15 - minor optimize asynconnect, I wish
- 0.20.14 - fix Redis connector's threading related error
- 0.20.4 - add Redis connector
- 0.20 - add API Gateway access handler

0.19 (Dec 2016)

- Reengineering was.request methods, fix disk caching

0.18 (Dec 2016)

- 0.18.11 - default content-type of was.post(), was.put() has
  been changed from 'application/x-www-form-urlencoded' to 'application/json'.
  if you use this method currently, you SHOULD change method name
  to was.postform()

- 0.18.7 - response contents caching has been applied to all
  was.request services (except websocket requests).

0.17 (Oct 2016)

- `Skitai WSGI App Engine Daemon`_ is seperated

0.16 (Sep 2016)

- 0.16.20 fix SSL proxy and divide into package for proxy & websocket_handler
- 0.16.19 fix HTTP2 cookie
- 0.16.18 fix handle large request body
- 0.16.13 fix thread locking for h2.Connection
- 0.16.11 fix pushing promise and response on Firefox
- 0.16.8 fix pushing promise and response
- 0.16.6 add several configs to was.app.config for
  limiting post body size from client
- 0.16.5 add method: was.response.hint_promise (uri) for
  sending HTP/2 PUSH PROMISE frame
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
.. _hyper-h2: https://pypi.python.org/pypi/h2
.. _loky: https://pypi.python.org/pypi/loky

