========================================
Skitai App Engine For Microservices
========================================

.. contents:: Table of Contents


Introduce
===========

Skitai is a kind of branch of `Medusa Web Server`__ - A High-Performance Internet Server Architecture.

Medusa is different from most other servers because it runs as a single process, multiplexing I/O with its various client and server connections within a single process/thread.

Skitai orients light-weight, simplicity and strengthen networking operations with external resources - HTTP / HTTPS / XML-RPC / PostgreSQL_ - keeping very low costs. And it is being optimized for building microservices.

- Working as Web, XML-RPC and Reverse Proxy Loadbancing Server
- HTML5 Websocket & HTTP/2.0 implemeted
- Handling massive RESTful API/RPC/HTTP(S) connections based on asynchronous socket framework at your apps easily
- Asynchronous connection pool with PostgreSQL, MongoDB and Redis

Skitai is not a framework for convinient developing, module reusability and plugin flexibility etc. It just provides some powerful communicating services for your WSGI apps as both server and client.

Also note it is inspired by Zope_ and Flask_ a lot.


Conceptually, Skitai has been seperated into two components:

1. Skitai App Engine Server, for WSGI apps

2. Skito-Saddle, the small WSGI container integrated with Skitai. But you can also mount any WSGI apps and frameworks like Flask.

.. _hyper-h2: https://pypi.python.org/pypi/h2
.. _Zope: http://www.zope.org/
.. _Flask: http://flask.pocoo.org/
.. _PostgreSQL: http://www.postgresql.org/
.. __: http://www.nightmare.com/medusa/medusa.html



Installation
=========================

**Requirements**

On win32, required `pywin32 binary`_

.. _`pywin32 binary`: http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/


**Installation**

.. code-block:: bash

    pip install skitai    

Another way from Git:

.. code-block:: bash

    git clone https://gitlab.com/hansroh/skitai.git
    cd skitai
    python setup.py install


But generally you don't need install alone. When you install Skitai App Engine, proper version of Skitai App Engine will be installed.


Starting Skitai
================


Basic Usage
------------

.. code:: python
  
  #WSGI App

  def app (env, start_response):
    start_response ("200 OK", [("Content-Type", "text/plain")])
    return ['Hello World']
    
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

  python app.py

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
- pref: supported by Saddle

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
      	pref.config.urllist.append (line.split ("\t", 4))


Logging and Console Displaying
--------------------------------

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


Run As Daemon
--------------

.. code:: bash
  
  python3 app.py start
  
  or 
  
  python3 app.py -d
  
For stopping daemon,

.. code:: bash
  
  python3 app.py stop


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


Mount Multiple WSGI Apps And Static Directories
------------------------------------------------

Here's three WSGI app samples:

.. code:: python
  
  #WSGI App

  def app1 (env, start_response):
    start_response ("200 OK", [("Content-Type", "text/plain")])
    return ['Hello World']
    
  app1.use_reloader = True
  app1.debug = True


  # Flask App*
  from flask import Flask  
  app2 = Flask(__name__)  
  
  app2.use_reloader = True
  app2.debug = True
  
  @app2.route("/")
  def index ():	 
    return "Hello World"


  # Skito-Saddle App  
  from skitai.saddle import Saddle  
  app3 = Saddle (__name__)
  
  app3.use_reloader = True
  app3.debug = True
    
  @app3.route('/')
  def index (was):	 
    return "Hello World"


Then place this code at bottom of above WSGI app.

.. code:: python
  
  if __name__ == "__main__": 
  
    import skitai
    
    skitai.mount ('/t1', __file__, 'app1')
    skitai.mount ('/t2', __file__, 'app2')
    skitai.mount ('/t3', __file__, 'app3')
    skitai.mount ('/', 'static')
    skitai.run ()

These feaure can used for managing version. 

Let's assume initail version of app file is app_v1.py.

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
   

Mounting With Virtual Host
-------------------------------

.. code:: python
  
  if __name__ == "__main__": 
  
    import skitai
    skitai.vmount ('www.site1.com', '/', 'site1.py')
    skitai.vmount ('www.site2.com', '/', 'site2.py')
    skitai.run ()
    
    
Enabling Proxy Server
------------------------

.. code:: python
  
  skitai.enable_proxy ()
  skitai.mount ('/', app)
  skitai.run ()

Adding Server(s) Alias
------------------------

Cluster should be defined like this: (alias_type, servers, role = "", source = "", ssl = False).

- alias_type: available database or protocol types are:

  - PROTO_HTTP
  - PROTO_HTTPS
  - PROTO_WS: websocket
  - PROTO_WSS: SSL websocket
  - DB_PGSQL
  - DB_SQLITE3
  - DB_REDIS
  - DB_MONGODB

- server: single or server list
- role (optional): it is valid only when cluster_type is http or https for controlling API access
- source (optional): comma seperated ipv4/mask
- ssl (optional): use SSL connection or not, PROTO_HTTPS and PROTO_WSS use SSL defaultly

.. code:: python
  
  skitai.mount ('/', app)
  skitai.alias (
    '@members', skitai.PROTO_HTTP, "members.example.com", 
    role = 'admin', source = '172.30.1.0/24,192.168.1/24'  
  )
  skitai.alias (
    '@mysqlite3', skitai.DB_SQLITE3, ["/var/tmp/db1", "/var/tmp/db2"]
  )  
  skitai.run ()

Run as HTTPS Server
------------------------

To genrate self-signed certification file:

.. code:: python

    openssl req -new -newkey rsa:2048 -x509 -keyout server.pem -out server.pem -days 365 -nodes


.. code:: python
  
  skitai.mount ('/', app)
  skitai.enable_ssl ('server.pem', 'key.pem', 'your pass phrase')
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
In case Flask, it seems 'url_for' generate url by joining with env["SCRIPT_NAME"] and route point, so it's not problem. Skito-Saddle can handle obiously. But I don't know other WSGI containers will work properly.


SMTP Delivery Agent
---------------------

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
--------------------

*New in version 0.26*

Sometimes app need batch tasks for minimum response time to clients. At this situateion, you can use taks scheduling tool of OS - cron, taks scheduler - or can use Skitai's batch task scheduling service for consistent app management.

.. code:: python
  
  skitai.cron ("*/2 */2 * * *", "/home/apps/monitor.py  > /home/apps/monitor.log 2>&1")
  skitai.cron ("9 2/12 * * *", "/home/apps/remove_pended_files.py > /dev/null 2>&1")
  skitai.mount ('/', app)  
  skitai.run ()
  
Taks configuarion is very same with posix crontab.


Asccessing File Reources On Startup
-------------------------------------

Skitai's working directory is where the script call skitai.run (). Even you run skitai at root directory,

.. code:: bash

  /app/example/app.py -d
  
Skitai will change working directory to /app/example on startup.

So your file resources exist within skitai run script, you can access them by relative path,

.. code:: python
  
  monitor = skital.joinpath ('appack', 'monitor.py')
  skitai.cron ("*/2 */2 * * *", "%s > /home/apps/monitor.log 2>&1" % monitor)

Also, you need absolute path on script,

.. code:: python

  skitai.getswd () # get skitai working directory


Enable Cache File System
------------------------------

If you make massive HTTP requests, you can cache contents by HTTP headers - Cache-Control and Expires

.. code:: python
  
  skitai.enable_cachefs (path = '/var/skitai/cache', memmax = 0, diskmax = 0)
  skitai.mount ('/', app)
  skitai.run ()
 
 
Configure Max Age For Static Files
--------------------------------------
  
You can set max-age for static files' respone header like,

..code:: bash

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
    
  @app.startup
  def startup (wasc):
    wasc.handler.set_auth_handler (Authorizer ())
    
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


Skitai with Nginx / Squid
---------------------------

From version 0.10.5, Skitai supports virtual hosting itself, but there're so many other reasons using with reverse proxy servers.

Here's some helpful sample works for virtual hosting using Nginx / Squid.

If you want 2 different and totaly unrelated websites:

- www.jeans.com
- www.carsales.com

Then you can reverse proxying using Nginx, Squid or many others.

Example Squid config file (squid.conf) is like this:

.. code:: python
    
    http_port 80 accel defaultsite=www.carsales.com
    
    cache_peer 192.168.1.100 parent 5000 0 no-query originserver name=jeans    
    acl jeans-domain dstdomain www.jeans.com
    http_access allow jeans-domain
    cache_peer_access jeans allow jeans-domain
    cache_peer_access jeans deny all
    
    cache_peer 192.168.1.100 parent 5001 0 no-query originserver name=carsales
    acl carsales-domain dstdomain www.carsales.com
    http_access allow carsales-domain
    cache_peer_access carsales allow carsales-domain
    cache_peer_access carsales deny all

For Nginx might be 2 config files (I'm not sure):

.. code:: python

    ; /etc/nginx/sites-enabled/jeans.com
    server {
	    listen 80;
	    server_name www.jeans.com;
      location / {
        proxy_pass http://192.168.1.100:5000;
      }
    }
    
    ; /etc/nginx/sites-enabled/carsales.com    
    server {
	    listen 80;
	    server_name www.carsales.com;
      location / {
        proxy_pass http://192.168.1.100:5001;
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

.. _`Skitai app examples`: https://gitlab.com/hansroh/skitai/tree/master/examples



Export API From Your Module Through Skitai
=============================================

If your module need export APIs or web pages, you can include app in your module for Skitai App Engine.

Let's assume your package name is 'unsub'.

Your app should be located at unsub/export/skitai/app.py

Then users uses your module can mount on skitai by like this,

.. code:: python
  
  import unsub
  
  pref = skitai.pref ()  
  pref.config.urlfile = skitai.joinpath ('resources', 'urllist.txt')
  
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
      	urllist.append (line.split ("\t", 4))
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



Async Requests Service
------------------------

Most importance service of 'was' is making requests to HTTP, REST, RPC and Database Engines. The modules related theses features from aquests_.

You can read aquests_ usage first.

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


Usage At Single Threaded Environment
`````````````````````````````````````

If you run Skitai with single threaded mode, you can't use req.wait(), req.getwait() or req.getswait(). Instead you should use callback for this, and Skitai provide async response.

.. code:: python
  
  def response_handler (response, proxy):
    proxy.done (response.content)
        
  @app.route ("/index")
  def aresponse_example (was):
    proxy = was.aresponse (response_handler)    
    proxy.get (None, "https://pypi.python.org/pypi/skitai")    
    return proxy

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
    
    skitai.run (
      clusters = {        
        '@mysearch': 
        ('https', ["s1.myserver.com:443", "s2.myserver.com:443"])
      },
      mount = ("/", app)
    )
  
  
It just small change from was.rpc () to was.rpc.lb ()

*Note:* If @mysearch member is only one, was.get.lb ("@mydb") is equal to was.get ("@mydb").

*Note2:* You can mount cluster @mysearch to specific path as proxypass like this:

.. code:: bash
  
  if __name__ == "__main__":
    import skitai
    
    skitai.run (
      clusters = {        
        '@mysearch': 
        ('https', ["s1.myserver.com:443", "s2.myserver.com:443"])        
      },
      mount = [
        ("/", app),
        ("/search", '@mysearch')
      ]
    )
  
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
    
    skitai.run (
      clusters = {        
        '@mydb': 
        (
          'postresql', 
          [
            "s1.yourserver.com:5432/mydb/user/passwd", 
            "s2.yourserver.com:5432/mydb/user/passwd"
          ]
        )
      },
      mount = [
        ("/", app)
      ]
    )
    

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


Caching Result
````````````````

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
- was.tojson (object)
- was.fromjson (string)
- was.toxml (object, usedatetime = 0) # XMLRPC
- was.fromxml (string) # XMLRPC
- was.togrpc (object) # gRPC
- was.fromgrpc (message, obj) # gRPC
- was.restart () # Restart Skitai App Engine Server, but this only works when processes is 1 else just applied to current worker process.
- was.shutdown () # Shutdown Skitai App Engine Server, but this only works when processes is 1 else just applied to current worker process.



HTML5 Websocket
====================

*New in version 0.11*

The HTML5 WebSockets specification defines an API that enables web pages to use the WebSockets protocol for two-way communication with a remote host.

Skitai can be HTML5 websocket server and any WSGI containers can use it.

But I'm not sure my implemetation is right way, so it is experimental and could be changable.

First of all, see conceptual client side java script for websocket.

.. code:: html
  
  <body>
  <ul id="display"></ul>
  <input id="mymsg" type="text">
  <button onclick='talk ();'>Submit<button>
  
  <script language="javascript" type="text/javascript">  
  var wsUri = "ws://localhost:5000/websocket/chat";
  testWebSocket();
  
  function testWebSocket()
  {
    websocket = new WebSocket(wsUri);
    websocket.onopen = function(evt) { onOpen(evt) };
    websocket.onclose = function(evt) { onClose(evt) };
    websocket.onmessage = function(evt) { onMessage(evt) };
    websocket.onerror = function(evt) { onError(evt) };
  }
  
  function onOpen(evt) {doSend("Hello");}
  function onClose(evt) {log_info ("DISCONNECTED");}  
  function onMessage(evt) {log_info('evt.data');}
  function onError(evt) {log_info('ERROR: ' + evt.data));}  
  function doClose () {websocket.close();}  
  function doSend(message) {
  	log_info('SENT: ' + message));
  	websocket.send(message);
  }
  function talk () {
    doSend ($("#mymsg").val());
    $("#mymsg").val("");
  }
  function log_info (message) {
   $('<li>' + message + '</li>').appendTo ("#display");
  }    
  </script>  
  </body>


If your WSGI app enable handle websocket, it should give  initial parameters to Skitai like this,

.. code:: python
  
  def websocket (was, message):
    if was.wsinit ():
      return was.wsconfig (
        websocket design specs, 
        keep_alive_timeout = 60, 
        message_encoding = None
      )		

*websocket design specs* can  be choosen one of 4.

WS_SIMPLE (before version 0.24, WEBSOCKET_REQDATA)

  - Thread pool manages n websocket connection
  - It's simple request and response way like AJAX
  - Use skitai initail thread pool, no additional thread created
  - Low cost on threads resources, but reposne cost is relatvley high than the others

WS_GROUPCHAT (New in version 0.24)
  
  - Trhead pool manages n websockets connection
  - Chat room model
  
WS_DEDICATE (before version 0.24, WEBSOCKET_DEDICATE_THREADSAFE)

  - One thread per websocket connection
  - Use when interactives takes long time like websocket version telnet or subprocess stdout streaming
  - New thread created per websocket connection
 

*keep alive timeout* is seconds.

*message_encoding*

Websocket messages will be automatically converted to theses objects. Note that option is only available with Skito-Saddle WSGI container.

  - WS_MSG_JSON
  - WS_MSG_XMLRPC


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
  if event == skitai.WS_EVT_INIT:
    return request.environ ['websocket.config'] = (...)
  if event == skitai.WS_EVT_OPEN:
    return ''
  if event == skitai.WS_EVT_CLOSE:
    return ''
  if event:
    return '' # should return null string
      
At Skito-Saddle, handling events is more simpler,

.. code:: python
  
  if was.wsinit ():
    return was.wsconfig (spec, timeout, message_type)    
  if was.wsopened ():
    return
  if was.wsclosed ():
    return  
  if was.wshasevent (): # ignore all events
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
    if was.wsinit ():
      return was.wsconfig (skitai.WS_SIMPLE, 60)
    elif was.wsopened ():
      return "Welcome Client %s" % was.wsclient ()
    elif was.wshasevent ():
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
    
    if was.wsinit ():
      num_sent [client_id] = 0      
      return was.wsconfig (skitai.WS_SIMPLE, 60)
    elif was.wsopened ():
      return
    elif was.wsclosed ():      
      del num_sent [client_id]
      return
    elif was.wshasevent ():
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


Group Chat Websocket
---------------------

This is just extension of Simple Data Request & Response. Here's simple multi-users chatting app.

This feature will NOT work on multi-processes run mode.

Many clients can connect by ws://localhost:5000/websocket/chat?roomid=1. and can chat between all clients.

.. code:: python

  @app.route ("/chat")
  def chat (was, message, room_id):   
    client_id = was.wsclient ()
    
    if was.wsinit ():
      return was.wsconfig (skitai.WS_GROUPCHAT, 60)    
    elif was.wsopened ():
      return "Client %s has entered" % client_id
    elif was.wsclosed ():
      return "Client %s has leaved" % client_id
      
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


Threadsafe-Dedicated Websocket
-------------------------------

It is NOT for general customer services. Please read carefully.

This spec is for very special situation. It will create new work thread and that thread handles only one  client. And The thread will be continued until message receiving loop is ended. It is designed for long running app and for limited users - firms's employees or special clients who need to use server-side resources or long applications take long time to finish and need to observe output message stream.

Briefly, it can be helpful for making web version frontend UI to controlling your backend application with jquery, HTML5 easily.

Client can connect by ws://localhost:5000/websocket/talk?name=jamesmilton.

.. code:: python

  class Calcultor:  
    def __init__ (self, ws):
      self.ws = ws
      self.p = None
      
    def calculate (self, count):
      self.p = Popen (
        [sys.executable, r'calucate.py', '-c', count],
        universal_newlines=True,
        stdout=PIPE, shell = False
      )    
      for line in iter(p.stdout.readline, ''):
        self.ws.send (line)	      
      self.p.stdout.close ()
      self.p = None
    
    def run (self, count):
      if self.p is None:
        threading.Thread (target = self.calculate, args = (count,)).start ()
        return 1
      
    def kill (self):
      if self.p:
        os.kill (self.p.pid)
        return 1
           
        
  @app.route ("/websocket/calculate")
  def calculate (was):
    if was.wsinit ():
      return was.wsconfig (skitai.WS_DEDICATE, 60)
    
    ws = was.websocket
    calcultor = Calcultor (ws)    
    while 1:
      m = ws.getwait ()
      if m is None: # client disconnected
        calcultor.kill ()
        break
                        
      if m.lower () == "bye":
        calcultor.kill ()
        ws.send ("Bye, have a nice day." + m)
        ws.close ()
        break
        
      elif m.lower () == "kill":  
        if calcultor.kill ():
          self.ws.send ('killed')	
        else:
          self.ws.send ('Error: not running')	   
        
      elif m.lower () [:3] == "run":
        if calcultor.run (int (m [3:].strip ())):
          self.ws.send ('started')	
        else:
          self.ws.send ('Error: already running')
        
      else:  
        ws.send ("You said %s but I can't understatnd" % m)

At Flask,

.. code:: python
  
  if request.environ.get ("websocket.event") == skitai.WS_EVT_INIT:
    request.environ ["websocket.config"] = (
      skitai.WS_GROUPCHAT, 
      60, 
      None
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
- appack: Directory, Module package for helping app like config.py, model.py etc...
- static: Directory, Static file like css, js, images. This directory would be mounted for using
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


Reloading App Package
-----------------------
  
If app.use_reloader is True, all module of appack - sub package directory of app.py - will be reloaded automatically if file is modified.


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
- was.request.body
- was.request.headers # case insensitive dictioanry
- was.request.args # dictionary contains url/form parameters
- was.request.routed_function
- was.request.routable # {'methods': ["POST", "OPTIONS"], 'content_types': ["text/xml"] }
- was.request.split_uri () # (script, param, querystring, fragment)
- was.request.json () # load request body as json
- was.request.get_header ("content-type") # case insensitive
- was.request.get_headers () # retrun header all list
- was.request.get_body ()
- was.request.get_scheme () # http or https
- was.request.get_remote_addr ()
- was.request.get_user_agent ()
- was.request.get_content_type ()
- was.request.get_main_type ()
- was.request.get_sub_type ()



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
- was.response.set_status (status) # "200 OK", "404 Not Found"
- was.response.get_status ()
- was.response.set_headers (headers) # [(key, value), ...]
- was.response.get_headers ()
- was.response.set_header (k, v)
- was.response.get_header (k)
- was.response.del_header (k)
- was.response.hint_promise (uri) # *New in version 0.16.4*, only works with HTTP/2.x and will be ignored HTTP/1.x


Useful Response Shortcuts
````````````````````````````

When In cases you want to retrun JSON, XMLRPC, gRPC or local file content, below methods will be useful.

.. code:: python

  @app.route ("/")
  def getjson (was):  
    return was.jstream ({'mydata': 'myvalue'})
  
  @app.route ("/<filename>")
  def getfile (was, filename):  
    return was.fstream ('/data/%s' % filename)    
    
- was.jstream (obj) # shortcut for was.response ("200 OK", was.tojson (obj), [("Content-Type", "application/json")])
- was.xstream (obj, usedatetime = 0) # shortcut for was.response ("200 OK", was.toxml (obj), [("Content-Type", "text/xml")])
- was.gstream (obj) # shortcut for was.response ("200 OK", was.togrpc (obj), [("Content-Type", "application/grpc")])
- was.fstream (abspath, mimetype = 'application/octet-stream') # return file stream object


Async Streaming Response
``````````````````````````

*New in version 0.24.8*

If you use was' requests services, and they're expected taking a long time to fetch, you can use async response.

- Async response has advantage at multi threads environment returning current thread to thread pool early for handling the other requests
- Async response should be used at single thread evironment. If you run Skitai with threads = 0, you can't use wait(), getwait() or getswiat() for receiving response for HTTP/DBO requests.

.. code:: python
  
  def response_handler (resp, proxy):
    if resp.status_code == 200:      
      proxy [resp.reqid]  = proxy.render (
        '%s.html' % resp.reqid,
        r = response
      )
    else:
      proxy [resp.reqid] = '<div>Error in %s</div>' % resp.reqid
      
    if proxy.fetched_all ():
      proxy.done (proxy.render_all ("example.html"))
      # or just join response data
      # proxy.done (proxy ['skitai'] + "<hr>" + proxy ['aquests'])

  @app.route ("/aresponse_example")
  def aresponse_example (was):
    proxy = was.aresponse (response_handler)    
    proxy.get ('skitai', "https://pypi.python.org/pypi/skitai")
    proxy.get ('aquests', "https://pypi.python.org/pypi/aquests")
    return proxy

'skitai.html' Jinja2 template used in render() is,

.. code:: html

  <div>{{ r.url }} </div> 
  <div>{{ r.text }}</div>

'example.html' Jinja2 template used in render_all() is,

.. code:: html

  <div>{{ skitai }}</div>
  <hr>
  <div>{{ aquests }}</div>

And you can use almost was.* objects at render() and render_all() like was.request, was.app, was.ab or was.g etc. But remember that response header had been already sent so you cannot use aquests features and connot set new header values like cookie or mbox (but reading is still possible).
  
Above proxy can make requests as same as was object except first argument is identical request name (reqid). Compare below things.

  * was.get ("https://pypi.python.org/pypi/skitai")
  * ResProxy.get ('skitai', "https://pypi.python.org/pypi/skitai")

This identifier can handle responses at executing callback. reqid SHOULD follow Python variable naming rules because might be used as template variable.

You MUST call ResProxy.done(content_to_send) finally, and if you have chunk content to send, you can call ResProxy.push(chunk_content_to_send) for sending middle part of contents before calling done ().

*New in version 0.25.2*

You can set meta data dictionary per requests if you need.

.. code:: python

  def response_handler (response, proxy):
    due = time.time () - response.meta ['created']
    proxy.push (response.content)
    proxy.push ('\n\nFetch in %2.3f seconds' % due)
    proxy.done () # Should call
    
  @app.route ("/aresponse_example")
  def aresponse_example (was):
    proxy = was.aresponse (response_handler)
    proxy.get ('req-0', "http://my-server.com", meta = {'created': time.time ()})    
    return was.response ("200 OK", proxy, [('Content-Type', 'text/plain')])

But it is important that meta arg should be as keyword arg, and DON'T use '__reqid' as meta data key. '__reqid' is used internally.

    
Creating async response proxy:

- was.aresponse (response_handler, prolog = None, epilog = None): return ResProxy, prolog and epilog is like html header and footer

response_handler should receive 2 args: response for your external resource request and ResProxy.

Note: It's impossible requesting map-reduce requests at async response mode.

collect_producer has these methods.

- ResProxy.get (), post (), ...
- ResProxy.fetched_all (): True if numer of requests is same as responses
- ResProxy.render (template_file, single dictionary object or keyword args, ...): render per response, and can assign into ResProxy like dictionary
- ResProxy.render_all (template_file): render all responses, in template file, reqids of each responses are used as template variable.
- ResProxy.push (content_to_send): push chunk data to channel
- ResProxy.done (content_to_send = None)


HTTP/2.0 Server Push
``````````````````````

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


Getting URL Parameters
-------------------------

.. code:: python
  
  @app.route ("/hello")
  def hello_world (was, num = 8):
    return num
  # http://127.0.0.1:5000/hello?num=100	
	
  @app.route ("/hello/<int:num>")
  def hello_world (was, num = 8):
    return str (num)
    # http://127.0.0.1:5000/hello/100


Also you can access as dictionary object 'was.request.args'.

.. code:: python

  num = was.request.args.get ("num", 0)


for fancy url building, available param types are:

- int
- float
- path: /download/<int:major_ver>/<path>, should be positioned at last like /download/1/version/1.1/win32
- If not provided, assume as string. and all space char replaced to "_'


Getting Form Parameters
----------------------------

Getting form is not different from the way for url parameters, but generally form parameters is too many to use with each function parameters, can take from single args \*\*form or take mixed with named args and \*\*form both.

.. code:: python

  @app.route ("/hello")
  def hello (was, **form):  	
  	return "Post %s %s" % (form.get ("userid", ""), form.get ("comment", ""))
  	
  @app.route ("/hello")
  def hello_world (was, userid, **form):
  	return "Post %s %s" % (userid, form.get ("comment", ""))


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

For using Chameleon_ template engine, you just make template file extention with '.pt' or '.ptal' (Page Template or Page Template Attribute Language).

.. code:: python
    
  return was.render ("index.ptal", choice = 2, product = "Apples")


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
- was.cookie.iterkyes ()
- was.cookie.itervalues ()
- was.cookie.iteritems ()


Access Session
----------------

was.session has almost dictionary methods.

To enable session for app, random string formatted securekey should be set for encrypt/decrypt session values.

*WARN*: `securekey` should be same on all skitai apps at least within a virtual hosing group, Otherwise it will be serious disaster.

.. code:: python

  app.securekey = "ds8fdsflksdjf9879dsf;?<>Asda"
  app.session_timeout = 1200 # sec
  
  @app.route ("/session")
  def hello_world (was, **form):  
    if "login" not in was.session:
      was.session.set ("user_id", form.get ("hansroh"))
      # or
      was.session ["user_id"] = form.get ("hansroh")

- was.session.set (key, val)
- was.session.get (key, default = None)
- was.session.source_verified (): If current IP address matches with last IP accesss session
- was.session.getv (key, default = None): If not source_verified (), return default
- was.session.remove (key)
- was.session.clear ()
- was.session.kyes ()
- was.session.values ()
- was.session.items ()
- was.session.has_key ()
- was.session.iterkyes ()
- was.session.itervalues ()
- was.session.iteritems ()


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


App and Method Decorators and was.g
-----------------------------------------

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
    
Also there're another kind of decorator group, App decorators.

.. code:: python

  @app.startup
  def startup (wasc):
    logger = wasc.logger.get ("app")
    # OR
    logger = wasc.logger.make_logger ("login", "daily")
    config = wasc.config
    wasc.register ("loginengine", SNSLoginEngine (logger))
    wasc.register ("searcher", FulltextSearcher (wasc.numthreads))    
  
  @app.onreload  
  def onreload (wasc):
    wasc.loginengine.reset ()
  
  @app.shutdown    
  def shutdown (wasc):
    wasc.searcher.close ()
        
    wasc.unregister ("loginengine")
    wasc.unregister ("searcher")
  
'wasc' is Python Class object of 'was', so mainly used for sharing Skitai server-wide object via was.object.

And you can access numthreads, logger, config from wasc.

As a result, myobject can be accessed by all your current app functions even all other apps mounted on Skitai.

.. code:: python
  
  # app mounted to 'abc.com/members'
  @app.route ("/")
  def index (was):
    was.loginengine.get_user_info ()
    was.searcher.query ("ipad")
  
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

These methods will be called,

1. startup: when app imported on skitai server started
2. onreload: when app.use_reloader is True and app is reloaded
3. shutdown: when skitai server is shutdowned


CORS (Cross Origin Resource Sharing) and Preflight
-----------------------------------------------------

For allowing CORS, you should do 2 things:

- set app.aloow_origin
- allow OPTIONS methods for routing

.. code:: python
  
  app = Saddle (__name__)
  app.acess_control_allow_origin = "*"
  app.acess_control_max_age = 3600
  
  @app.route ("/post", methods = ["POST", "OPTIONS"])
  def post (was):
    args = was.request.json ()	
    return was.jstream ({...})	


Building Cache With App Decorator
----------------------------------

New in version 0.26

If you have pre-defined database cluster, and want to create cache object on app starting, you can use was.ajob method.

.. code:: python
  
  app.cache = {}
  
  def create_cache (res):
    for row in res.data:
      app.cache ['STATENAMES'][row.code] = row.name
  
  @app.startup
  def startup (wasc):
    wasc.ajob ('@mydb', create_cache).execute ("select code, name from states;")
	
Now you can access cache by was.app.cache or app.cache.
	

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


Building for Larger App
-------------------------

You have 2 options for extending your app scale.

1. Mount multiple microservices
2. Mount saddlery on saldde

Mount Multiple Microservices
``````````````````````````````

I personally recommend this way by current developing trend.

.. code:: python
  
  import skitai    
  
  skitai.run (
    mount = [
      ('/service', ('/service/app', 'app')),
      ('/service/trade', ('/service/trade/app', 'app')),
      ('/service/intro', ('/service/intro/app', 'app')),
      ('/service/admin', ('/service/admin/app', 'app')),
      ('/', '/service/static')
    ]
  )

And your pysical directory structure is,

.. code:: bash

  /service/app.py
  /service/templates/*.html
  /service/apppackages/*.py
  
  /service/trade/app.py
  /service/trade/templates/*.html  
  /service/trade/apppackages/*.py
  
  /service/intro/app.py
  /service/intro/templates/*.html
  /service/intro/apppackages/*.py
  
  /service/admin/app.py
  /service/admin/templates/*.html
  /service/admin/apppackages/*.py
  
  /service/static/images
  /service/static/js
  /service/static/css
  
This structure make highly focus on each microservices and make easy to move or apply scaling by serivce traffic increment.

Mount Saddlery On Saddle
``````````````````````````

If your app is very large or want to manage codes by categories, you can seperate your app.

admin.py
  
.. code:: python

  from skitai.saddle import Saddlery
  part = Saddlery ()
  
  @part.route ("/<name>")
  def hello (was):
    # can build other module's method url
    return was.ab ("index", 1, 2) 

app.py

.. code:: python

  from skitai.saddle import Saddle
  from . import admin
  
  app = Saddle (__name__)
  app.debug = True
  app.use_reloader = True  
  app.mount ("/admin", admin, "part")
  
  @app.route ("/")
  def index (was, num1, num2):  
    return was.ab ("hello", "Hans Roh") # url building
        
Now, hello function's can be accessed by '/[app mount point]/admin/Hans_Roh'.
  
App's configs like debug & use_reloader, etc, will be applied to packages except decorators.

*Note:* was.app is always main Saddle app NOT current Saddlery sub app.

Saddlery can have own sub saddlery and decorators.

.. code:: python
  
  from skitai.saddle import Saddlery
  from . import admin_sub
  
  part = Saddlery () # mount point
  # Saddlery also can have sub Saddlery
  part.mount ("/admin/sub", admin_sub, "app")
  
  @part.startup
  def startup (wasc):
    wasc.register ("loginengine", SNSLoginEngine ())
    wasc.register ("searcher", FulltextSearcher ())    
  
  @part.shutdown    
  def shutdown (wasc):
    wasc.searcher.close ()
        
    wasc.unregister ("loginengine")
    wasc.unregister ("searcher")
    
  @part.before_request
  def before_request (was):
    if not login ():
      return "Not Authorized"
  
  @part.teardown_request
  def teardown_request (was):
    was.g.resouce.close ()
    ...
  
  @part.route ("/<name>")
  def hello (was):
    # can build other module's method url
    return was.ab ("index", 1, 2) 

In this case, app and sub-app's method decorators are nested executed in this order.

.. code:: python

  app.before_request()
    sub-app.before_request()
      hello()
    sub-app.finish_request() or package.failed_request()
    sub-app.teardown_request ()
  app.finish_request() or app.failed_request()
  app.teardown_request ()


**Saddlery and Jinja2 Templates**

was.render (template_path) always find templates directory where app.py exists, even if admin.py is located in sub directory with package form. This is somewhat conflicated but I think it's more easier way to maintain template files and template include policy. Remeber one app can have one templates directoty. But you can seperate into templates files by sub directory. For example:

.. code:: python

  /app.py
  /admin.py
  /members/__init__.py
  /static
  /templates/includes/header.html  
  /templates/includes/footer.html
  /templates/app/index.html  
  /templates/admin/index.html
  /templates/members/index.html

But if you want to use independent templates under own templates directory:

.. code:: python

  from skitai.saddle import Saddlery
  
  part = Saddlery (__name__)
  
  @part.route ("/<name>")
  def hello (was):
    return was.render2 ("show.htm", name = name)


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
  
  
Server Side:

.. code:: python
  
  import route_guide_pb2
  
  @app.route ("/GetFeature")
  def GetFeature (was, point):
    feature = get_feature(db, point)
  if feature is None:
    return route_guide_pb2.Feature(name="", location=point)
  else:
    return feature

  if __name__ == "__main__":
    skitai.run (
      mount = [('/routeguide.RouteGuide', app)
    )

For more about gRPC and route_guide_pb2, go to `gRPC Basics - Python`_.

Note: I think I don't understand about gRPC's stream request and response. Does it means chatting style? Why does data stream has interval like GPS data be handled as stream type? If it is chat style stream, is it more efficient that use proto buffer on Websocket protocol? In this case, it is even possible collaborating between multiple gRPC clients.

.. _`gRPC Basics - Python`: http://www.grpc.io/docs/tutorials/basic/python.html


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
==============
  
  0.26 (Apr 2017)
  
  - 0.26
    
    - support CORS (Cross Origin Resource Sharing)
    - support PATCH method
    - runtime app preferences and add __init__.bootstrap (preference)
    - fix route caching
    - auto reload sub modules in appack directory, if app.use_reloader = True
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
  - 0.25.3 aresponse response handler args spec changed, class name is cahnged from AsyncResponse to ResProxy
  - 0.25.2 fix aresponse exception handling, aresponse can send streaming chunk data
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
