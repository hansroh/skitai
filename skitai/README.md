# Skitai App Engine Library

Skitai App Engine Library (SAEL) is a kind of branch of [Medusa Web Server](http://www.nightmare.com/medusa/medusa.html) - A High-Performance Internet Server Architecture.

Medusa is different from most other servers because it runs as a single process, multiplexing I/O with its various client and server connections within a single process/thread.

SAEL orients light-weight and strengthen networking operations with external resources - HTTP / HTTPS / RPC / [PostgreSQL](http://www.postgresql.org/) - keeping low costs.

- It can run as XML/JSON-RPC & Web Server.
- It can request massive RPC/HTTP(S) connections based on asynchronous socket framework at your apps easily.
- Provide asynchronous PostgreSQL query execution

It also influenced by [Zope](http://www.zope.org) and [Flask](http://flask.pocoo.org) a lot.



## At Glance

### Installation
    pip install skitai


### Configuration

    [server]
    processes = 1
    threads = 4
    port = 5000
    ssl = no

    [routes:line]
    / = /home/skitaid/app/static
    / = /home/skitaid/app/webapp

Save this to 'devel.conf'

### Run Skitaid
    python server.py -f devel -c

### Your First XML-RPC App

edit /home/skitaid/app/webapp.py

    from skitai.server import ssgi
    
    app = ssgi.Application (__name__)
    app.set_devel (True)
    	
    @app.route ("/hello")
    def hello (was):
    	return 'Hello World'

It's similar to Flask App.

### Now Call

    import xmlrpclib

    s = xmlrpclib.Server ("http://127.0.0.1:5000/RPC2")
    s.hello ()

You can also load from your web browser by typing 'http://127.0.0.1:5000/hello'

### Your Second XML-RPC App For XML-RPC Map-Reduce

Add this lines to your config file

    [@mysearch]
    members = s1.yourserver.com:5000,s2.yourserver.com:5000,s3.yourserver.com:5000

Let's assume those servers are serving XML-RPC.

Your app:

    @app.route ("/search")
    def search (was, keyword = "Mozart"):
      s = was.map ("mysearch/rpc2")
      s.search (keyword)

      results = s.getswait (timeout = 2)

      all_results = []
      for result in results:
        if result.status == 3:
          all_results.extend (result.data)
      return all_results


Access url http://127.0.0.1:5000/search?keyword=Beethoven

The most important thing is:

All socket IO operations with members of @mysearch are working in asyncore module's poll () loop of Main Thread.

It's lower costs than multi-threading way.

Of cause, above app method is run in threads pool.

### Your Third App For PostgreSQL Map-Reduce

Add this lines to your config file

    [@mydb]
    type = postresql
    members = s1.yourserver.com:5432/mydb/user/passwd,s2.yourserver.com:5432/mydb/user/passwd,s3.yourserver.com:5432/mydb/user/passwd

Your app:

    @app.route ("/query")
    def query (was, keyword):
      s = was.dmap ("mydb")
      s.execute("SELECT * FROM CITIES;")

      results = s.getswait (timeout = 2)

      all_results = []
      for result in results:
        if result.status == 3:
          all_results.append (result.data)
      return all_results

## Installation & Configure

### Pre Requirements

#### Win32
- pywin32 binary - http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/
- psycopg2 binary - http://www.stickpeople.com/projects/python/win-psycopg/

(Optional)
- M2Crypto binary - https://github.com/saltstack/salt-windows-install/tree/master/deps/win32-py2.7
- jsonrpclib for serving JSON-RPC, use 'pip install jsonrpclib'
- Jinja2 for HTML Rendering, use 'pip install jinja2 '

#### Posix

    pip install jsonrpclib
    pip install m2crypto
    pip install jinja2
    pip install psycopg2

### Install Skitai Library

     pip install skitai

or download from

  https://pypi.python.org/pypi/skitai


### Install Skitaid

__Skitaid is an example implementation server using SAEL__.

In your install dir (ex: python/Lib/site-packages/skitai)

copy all files from implements/sktaid to any location you want 

like /home/skitaid, c:\skitaid


### Configure Skitaid

Review and edit: 

- /home/skitaid/etc/skitaid/skitaid.conf
- /home/skitaid/etc/skitaid/servers-enabled/sample.conf

then __copy/move__ /home/skitaid/etc/skitaid to __/etc/__ (On Win32 copy to __c:\etc\__)


### Startup Skitaid

#### Run in Console

    cd /home/skitaid/bin
    python server.py -c -f sample

For more detail switch,

    python server.py --help

Then go to http://127.0.0.1:5000/ using your web browser

#### Run as Service

There's two scripts for starting Skitaid server.

skitaid/bin/skitaid.py will start multiple server instances in all /etc/skitaid/servers-enabled directory.

skitaid/bin/server.py will start single server instance by command line switch -f [config file name (do not write .conf)]

Here's some example for running skitaid.py as service.

##### Liunx
Edit example script under skitaid/etc/init (Ubuntu) & init.d (CentOS)

then copy /etc/init or /etc/init.d by your OS env.

##### Win32

Go to skitaid/bin/win32service

    install_win32_service.py --startup auto install


### Shutdown Skitaid

If you start with server.py, Ctrl-C is good.

Else if skitaid.py

    python skitaid.py stop

For more detail switch, 

    python skitaid.py --help

Else if runnig as service,

    sudo skitaid stop
    or
    sudo service skitaid stop

### Configuration Detail

    [server]
    threads = 4
    
    ; Number of Workers, Posix Only
    processes = 1
    ip = 
    port = 5000
    ssl = no
    sessiontimeout = 1200
    
    ; Careful, Skitai's (forward) proxy is just experimental purpose.
    ; If you set yes, there's no way to control access to this server from anybody,
    ; except your firewall setting
    proxy = no
    
    ; Max-age header value for static files
    static_max_age = 300
    
    ; Number of RPC/RDBMS Result Cache
    num_result_cache_max = 200
    
    ; SESSION EN/DECRYPT KEY
    securekey = ASDF34x5=DFu$3FD45i&*YTnU+78
    
    ; For HTTP 401 Basic Authorization, It's not secure.
    admin_password = admin-password
    
    [certification]
    ; For HTTPS Service
    ; Default path is /etc/skitaid/etc/cert
    ; or write full path
    ;certfile = skitai.com.server.pem
    ;cafile = skitai.com.ca.pem
    ;passphrase = passphrase
    
    [routes:line]
    ; Change to proper pathes
    ; Skitai find file in D:\skitaid\app\static first, 
    ; if cant' find, refind method of D:\skitaid\app\webapp module
    / = /home/skitaid/app/static
    / = /home/skitaid/app/webapp

Especially, You should change securekey=. This value is used to encrypting session values, so change very random securekey.

processes and threads value is usally recommended, 

    processes = [number of CPUs]
    threads = 4

* _Note 1: Threads value is per one process_

* _Note 2: On win32 processes should be '1'. I don't know how to create multi-workers at win32._


## Quick Start

### Hello World

First of all, configure app location:

    [routes:line]    
    /test/ = /home/skitaid/app/webapp

And you make app at /home/skitaid/app/webapp.py:

    from skitai.server import ssgi
    app = ssgi.Application (__name__)
    app.set_devel (True)
    
    @app.route ("/")
    def wget (was, url):
    	return "Hello"

Done.

You can access, http://127.0.0.1:5000/test/


### Routing
If you configure,
				
    /test = /home/skitaid/app/webapp

/test/ is working like directory, but /test is like file.

It makes somewhat differnces inner 'a href' links.

    /test = /home/skitaid/app/test
    /test = /home/skitaid/app/webapp
    
    
It's a little confusing, but is not.

Above /home/skitaid/app/test is directory, and /home/skitaid/app/webapp is webapp.py

So Skitaid find first /home/skitaid/app/test/index.htm (of index.html).

If not exists, find method of /home/skitaid/app/webapp.py.

Bottom line, always psysical file has priority.


    @app.route ("/hello/world")
    def wget (was, url):
    	return "Hello"

/test is base url for /home/skitaid/app/webapp, then full translated to

    http://127.0.0.1:5000/test/hello/world
    
    or as XML-RPC,    
    s.test.hello.world ()
    

One more example,

    / = /home/skitaid/app/webapp

and

    @app.route ("/hello/world")
    def wget (was, url):
    	return "Hello"
    	
finally,

    http://127.0.0.1:5000/hello/world
    
    or as XML-RPC,    
    s.hello.world ()
    	
### Set App Development Mode
    
    app.set_devel (True)

If this is not set True, This app will be never reloaded whether you modify webapp.py or not.

At real service situation, it would be better perfomance False, and False is Default.  

    
### What is 'was'?

All app method's 1st arg is 'was'.

    def wget (was, url):
        return "Hello"
        
'was' is similar to 'self' in class instance method.

Imagine your app methods is App Server Class' methods.

'was` provide some objects and methods below:

#### Request Objects & Streaming
##### was.app

It's alias for:

    app = ssgi.Application (__name__)

    
##### was.request
##### was.cookie
##### was.session
##### was.env

#### Server Resources
##### was.apps
##### was.cachefs
##### was.rcache
##### was.httpserver
##### was.lifetime
##### was.queue
##### was.threads
##### was.cluster[socketpool]
##### was.cluster[dbpool]
##### was.cluster[@user-configured-clusters]
##### was.[user-registered-objects]

#### View Server Status
##### was.status()

    Table of Content

    APPS
    CACHEFS
    CLUSTER:__dbpool__
    CLUSTER:__socketpool__
    CLUSTER:blade
    CLUSTER:openfos
    CLUSTER:postgres
    ENVIRON
    HTTPSERVER
    LIFETIME
    QUEUE
    RCACHE
    THREADS
        
#### Object Serialize
##### was.tojson ()
##### was.toxml()

#### Switch Streaming Response
##### was.tostream()

#### Asynchronous Network Related Services
##### was.wget()
##### was.map()
##### was.lb()
##### was.db()
##### was.dmap()
##### was.dlb()



### Building Larger App

If you add another module named greetings.py at same directory as webapp.py

greetings.py:

    from skitai.server import ssgi
    
    package = ssgi.Package ()
    	
    @package.route ("/greeting/morning")
    def morning (was):
    	return 'good Morning'

and some modified webapp.py is:

    from skitai.server import ssgi
    import greetings
    
    app = ssgi.Application (__name__)
    app.set_devel (True)
    
    @app.startup
    def startup (wasc, app):
    	app.add_package (greetings)
    
    @app.route ("/hello/world")
    def wget (was, url):
    	return "Hello"
 
Added lines are:

    @app.startup
    def startup (wasc, app):
    	app.add_package (greetings)

This means when app is initailized, add greetings sub-package.

Sub-package inherit app's devel mode, base routing url.


There are 2 more app methods,

    @app.onreload
    def onreload (wasc, app):
    	pass
    	
    @app.shutdown
    def shutdown (wasc, app):
    	pass

There are new variable 'wasc', not 'was', it's class object of 'was', you can call class method register(), register an object to sharing with all the other apps.

    wasc.register ('object-alias', object)
    
but instanced 'was' doesn't have register() method.

### More About App Contructor / Deconstructor

It's useful this case, some object should be alive with app engine's lifetime.
    
    # automatically called only once when app engine starts
    @app.startup
    def startup (wasc, app):
    	app.searcher = Searcher ()
    	# for sharing with other apps
    	# all other apps can access as 'was.searcher'
    	wasc.register ("searcher", app.searcher)
    
    # automatically called when you modify this file and if set_devel is True
    @app.onreload
    def onreload (wasc, app):
    	# re-seting
    	app.searcher = wasc.searcher
    
    # automatically called only once when app engine enters shutdown process
    @app.shutdown		
    def shutdown (wasc, app):
    	# it's same as wasc.searcher.close ()
    	app.searcher.close ()
    	wasc.unregister ("searcher")

    	
### Accessing Request

### Getting Args
#### Fancy URL
#### URL Query String
#### Form

### Map-Filter-Reduce (MFR) Operation

### RPC Load-Balacing

### Rendering HTML with Jinja2 Template

### Cookie & Session

### Streaming Response

### File Upload

### Load-Balancing Reverse Proxy

### (Forward) Proxy

### Run HTTPS Server

### Virtual Hosting with Nginx / Squid

### Developing and Deploying Process

### Use Cases











