# Skitai App Engine Library

Skitai App Engine Library (SAEL) is a kind of branch of [Medusa Web Server](http://www.nightmare.com/medusa/medusa.html) - A High-Performance Internet Server Architecture.

Medusa is different from most other servers because it runs as a single process, multiplexing I/O with its various client and server connections within a single process/thread.

SAEL orients light-weight,simplicity  and strengthen networking operations with external resources - HTTP / HTTPS / RPC / [PostgreSQL](http://www.postgresql.org/) - keeping low costs.

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

'was` provide some objects related with request:
    
- was.request
- was.cookie
- was.session
-  was.environ
  
 And provide some asynchronous networking methods: 
 
- was.wget()
- was.map()
- was.lb()
- was.db()
- was.dmap()
- was.dlb()

These will be explained detail continued chapters.

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

Get request infomation:
    
    was.request.get_header ("content-length")
    was.request.get_raw_header ()
    
    path, param, querystring, fragment =  was.request.split_uri ()
    # access raw form or multipart data (if <= 5MB)
    was.request.get_body ()
    # get/head/post/put ...
    was.request.command
    # HTTP version
    was.request.version
    was.request.uri
    
    if was.request.command == "get":
      was.request.set_response (405, "Method Not Allowed")
      return "Not allowed get method for %s" % was.request.uri


Set response information:
    
    was.response.start (405, "Method Not Allowed")
    
    was.response ["Location"] = "/newloc"    
    was.response.set ("Location", "/newloc")
    was.response.update ("Content-Transfer-Encoding", "gzip")
    was.response.delete ("Content-Length")
    was.response.has_key ("Content-Type")
    was.response.instant (100)
    
    return  was.response.error (307)
    


### Environment

    was.env = {
      "HTTP_ACCEPT": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=",
      "HTTP_ACCEPT_ENCODING": "gzip",
      "HTTP_ACCEPT_LANGUAGE": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
      "HTTP_CACHE_CONTROL": "max-age=0",
      "HTTP_COOKIE": "SESSION=O5eMHORahMJqsYSiiF2iZLGK0eA=?_",
      "HTTP_USER_AGENT": "Mozilla/5.0 (Windows NT 6.1; rv:38.0) Gecko/20100101 Fir/38.0",
      ...
    }

### Getting Args

#### Fancy URL

    @app.route ("/company/<int:cid>/<cname>")
    def company (was, cid, cname):
      return "%d - %s" % (cid, cname)
 
 It can call, http://127.0.0.1:5000/company/555/Skitai+Corp
     
 Vaild types are int, float, path. If not specified, It is assumed string type.
    
#### URL Query String & Form Data

    @app.route ("/company")
    def company (was, cid, cname):
      return "%d - %s" % (cid, cname)

It can call by both *POST/GET*, 

    http://127.0.0.1:5000/company?cid=555&cname=Skitai+Corp

Actually, Args can be mixed with theses 3 methods.

It means also possible:

    @app.route ("/company/<int:cid>")
    def company (was, cid, cname):
      return "%d - %s" % (cid, cname)

     http://127.0.0.1:5000/company/555&cname=Skitai+Corp

 If args' name is duplicated like this: 
 
     http://127.0.0.1:5000/company/555&cname=Skitai+Corp&cid=333
 
Var name 'cid' will be convert to list type **["333", "444"].**

If there's so many args, just get as dictionary:

     def company (was, **form):
         form.get ("cid")
         form.get ("cname")


### Requesting HTTP(S), RPC

You can access HTTP/HTTPS Web page or RPC Server with asynchronously.

HTTP/HTTPS

    @app.route ("/test/wget")
    def wget (was, url = "https://www.python.org"):
        s = was.wget (url)
                
        rs = s.getwait (timeout = 2)
        if rs.status == 3:
            return "<pre>" + rs.data.replace ("<", "&lt;").replace ("<", "&gt;") + "</pre>"
 
If POST Request,
     
     s = was.wget (url, {"cid": "555", "cname="Skitai Corp"})
     
 
 If File Upload Request,
 
     s = was.wget (
     	url, 
     	{"cid": "555", "cname="Skitai Corp", "file": open ("/data/logo.gif")}, 
     	multipart = True    
     )
    
 RPC
    
    @app.route ("/test/rpc")
    def rpc (was):
        s = was.rpc ("https://www.python.org/rpc2")
        s.query ( "Beethoven")
        return str (s.getwait (timeout = 2))


### Map-Filter-Reduce (MFR) Operation
 
 At first, you configure members like this:   
    
    [@myrpcs]
    members = s1.yourserver.com:5000,s2.yourserver.com:5000,s3.yourserver.com:5000

Then you can MFR operation using 'mysearch'.

Fisrt example is simple Map-Reduce:

    @app.route ("/test/map")
    def map (was):
        s = was.map ("myrpcs/rpc2")    
        # we can expect [4.7,76,7,7]
        s.generate_random_int_list (5)
        
        all = []
        for rs in s.getswait (5):
            if rs.status == 3:
                all.extend (rs.data)
        
        return reduce (lambda x,y: x+y, all)    
    
If it maybe not need filter operation in ideal situaltion, at real world we sometimes need filter. 

Here's Map-Filter-Reduce example:

    @app.route ("/test/map")
    def map (was):        
        def select_func (rs):
          if rs.status == 3:
            rs.data =  filter (lambda x: x < 10, rs.data)
          else:
            rs.data = []  
        
        s = was.map ("myrpcs/rpc2", filter = select_func)
        # we can expect [4.7,76,7,7]
        s.generate_random_int_list (5)
        
        all = []
        for rs in s.getswait (5):
            all.extend (rs.data)
        
        return reduce (lambda x,y: x+y, all)    
 
 
 Why dosen't do filter after getswait () ?
 
 Because that way make  filter action be worked for waiting another results. We can save time.
    
    
### RPC Load-Balacing

You an load balncing to configures members with was.lb ():

At config file:

    [@mysearch]
    ssl = no
    members = s1.yourserver.com:5000,s2.yourserver.com:5000,s3.yourserver.com:5000

Your app is:

    @app.route ("/search")
    def search (was, keyword = "Mozart"):
      s = was.lb ("mysearch/rpc2")
      s.search (keyword)
      return s.getwait (timeout = 2)

### Connect to PostgreSQL

First of all you shuld know, there's some limitations, in asynchronous mode.

> There are several limitations in using asynchronous connections: the connection is always in autocommit mode and it is not possible to change it. So a transaction is not implicitly started at the first query and is not possible to use methods commit() and rollback(): you can manually control transactions using execute() to send database commands such as BEGIN, COMMIT and ROLLBACK. Similarly set_session() can¡¯t be used but it is still possible to invoke the SET command with the proper default_transaction_... parameter.

> With asynchronous connections it is also not possible to use set_client_encoding(), executemany(), large objects, named cursors.

> COPY commands are not supported either in asynchronous mode, but this will be probably implemented in a future release.

> from http://initd.org/psycopg/docs/advanced.html

    @app.route ("/test/db")
    def db (was):
    	s = was.db ("127.0.0.1:5432", "mydb", "postgres", "password")
    	s.execute ("SELECT * FROM weather;")
    	rs = s.getwait (2)    	
    	return "%s" % rs.data [0:10]
	
### PostgreSQL Map-Filter-Reduce (MFR) Operation
 
At first, you configure members like this:   
    
    [@mydbs]
    type = posgresql    
    members = s1.yourserver.com:5432/mydb/user/pass,s2.yourserver.com:5432/mydb/user/pass

Then you can MFR operation using 'mysearch'.

Fisrt example is simple Map-Reduce for getting top population city:

    @app.route ("/test/map")
    def top_city (was):
        s = was.dmap ("mydbs")    
        # we expect [{"name": "Fairfax", "population": 23478}, ...]
        s.execute ("SELECT name, population from CITIES;")
        
        all = []
        for rs in s.getswait (5):
            if rs.status != 3: continue
            all.extend ([(each ["city"],each ["population"]) for each in rs.data])
        all.sort (lambda x, y: cmp (y [0], x [0]))
        return all [0]
    
And inspite of very foolish, here's Map-Filter-Reduce example:

    @app.route ("/test/map")
    def map (was):        
        def filter_little (rs):
          if rs.status == 3:
          	rs.data =  filter (lambda x: x ["population"] >= 100000, rs.data)          	
          else:
            rs.data = []
            
        s = was.dmap ("mydbs", filter = filter_little)    
        # we expect [{"name": "Fairfax", "population": 23478}, ...]
        s.execute ("SELECT name, population from CITIES;")
        
        all = []
        for rs in s.getswait (5):
            all.extend ([(each ["city"],each ["population"]) for each in rs.data])        
        all.sort (lambda x, y: cmp (y [0], x [0]))
        return all [0]
 
    
### PostgreSQL Load-Balacing

Same config file, and your app is:

    s = was.dlb ("mydbs")    
    s.execute ("SELECT name, population from CITIES;")
    return s.getwait (2)
      
### RPC/PosgreSQL Caching

At config, 

    num_result_cache_max = 2000
    
means  maximum number of  RPC/PosgreSQL Results

    s = was.dlb ("mydbs")    
    s.execute ("SELECT name, population from CITIES;")
    result =  s.getwait (2)
    # cache for 300 sec.
    result.cache (timeout = 300)

    s = was.map ("myrpcs/rpc2")    
    s.generate_random_int_list (5)
    results = s.getswait (5):
    results.cache (timeout = 60)
    
### Rendering HTML with Jinja2 Template
Directory structure is:

    /home/skitaid/app/webapp.py
                     /static
                     /tempates/index.html
    
Now you can get_template () from app:
  
    @app.route ("/")
    def main (was):
        template = was.app.get_template ('index.html')
        d = {"url": urllib.quote ("https://pypi.python.org/pypi")}
        return str (template.render (d))
    
    
### Cookie & Session

For using session, should be enabled first,

    app = ssgi.Application (__name__)
    app.set_devel (True)
    app.use_session (True)

Signin:

    @app.route ("/test/signin")
    def sesscookie (was, username):
        if was.session.get ("logined"):
            return 'Already Loggin as %s' % was.cookie.get ("username")
            
        if username == "hansroh":
            was.cookie.set ("username", username)
            was.session.set ("logined", True)        
            return 'Welcome %s' % (was.cookie.get ("username"))
        
        else:
            return 'Sorry, You have no permission'

Sign Out:

    @app.route ("/test/signout")
    def sesscookie (was):
        del was.session ["logined"]        
        return '%s, Sign Out Success' % was.cookie.get ("username")    
    
### Before and After Request, Teardown (BAT) Automation

Let's assume you require log in at your app.

    @app.before_request
    def before_request (was):
    	if not is_logged_in ():
    		return LOGIN_FORM
    
    @app.after_request
    def after_request (was):
    	log_user_behavior ()
    
    @app.teardown_request
    def teardown_request (was):
    	return SORRY_MSG

Now, automatically called before/after/teardown functions in  all app's method.
    
     @route ("/myorders")
     def myorders (self):
        return ORDER_LIST (was.cookie ["userid"])
     
     @route ("/mycart")
     def mycart (self):
        return CART_LIST (was.cookie ["userid"])   

Exactly call mechanism is:

    if before_request:
      response = before_request (was)
      if response:
        reply (response)
        return
    
    try:
      response = myorder(was)
    except:
      if teardown_request:
        response = teardown_request(was)
      else:
        send 500 error to client
        return
    
    reply (response)
    

Also ssgi.package has BAT. For more detail, see *Building Larger App* section again.

greetings.py:

    @package.before_request
    def before_request (was):
    	if not is_logged_in ():
    		return LOGIN_FORM
    
    @package.route ("/morning")
    def morning (was):
      return "Good Morning"

and register greetings.py at webaap.py    		
    
    import greetings
    
    @app.startup
    def startup (wasc, app):
        app.add_package (greetings)

In this case calling sequence is:
    
    app.before_request()
    package.before_request()
    package.user_requested_method()
    package.after_request() or package.teardown_request()
    app.after_request() or app.teardown_request()

            
### Streaming Response
  
 You can return large data, but might be occured some problems - slow response, and occupying thread.
 
 So you can make class has method 'more' and optional 'abort':
    
    @app.route ("/streaming")
    def Stream (was, filename):
      class Stream:
        def __init__ (self, filename):          
          self.f = open (filename, "rb")
        
        def close (self):
          self.f.close ()
        
        def abort (self):
          # it will be called slient channel is suddnely disconnected
          self.close ()
            
        def more (self):
          data = self.f.read (4096)
          if not data:
          	self.close ()
          return data
      
      was.request ["Content-Type"] = "video/mp4"
      was.request ["Cache-Control"] = "max-age=0"
      return Stream (filename)
      
      
### File Upload

    <form action = "/test/up" enctype="multipart/form-data" method="post">
        <input type="hidden" name="submit-hidden" value="Hidden">   
        <p></p>What is your name? <input type="text" name="submit-name" value="Hans Roh"></p>
        <p></p>What files are you sending? <br />
        <input type="file" name="file">        
        </p>
        <input type="submit" value="Send"> 
        <input type="reset">
    </form>


    @app.route ("/test/up")
    def up (was, **karg):
        return str (karg) + "<hr>" + str (was.request.get_body ())
        
karg is like this:
    
    krgs = {
    'submit-hidden': 'Hans Roh', 
    'file': {'mimetype': 'application/octet-stream', 'local': '/tmp/tmposndlr', 'remote': 'study.sql', 'size': 511}
    }

        

### Load-Balancing Reverse Proxy

Your congig file:
    
    [routes:line]
    /viewinfo = @mywebservers
    
    [@mywebservers]
    ssl = no
    members = 192.168.1.100:5000,192.168.1.101:5000,192.168.1.102:5000 
    
You can call like this,

    http://127.0.0.1/viewinfo/view?id=555

### (Forward) Proxy

Proxy is maden just experimental purpose. 

There's no way to control access to this server from anybody except your firewall setting.

    [server]
    proxy = yes

then configuration your browser's proxy setting.

### Run HTTPS Server

At config:

    [certification]
    certfile = skitai.com.server.pem
    cafile = skitai.com.ca.pem
    passphrase = [passphrase]
    
For generating certfile an cafile using openSSL, see /etc/skitaid/cert/generate/README.txt
    
### Virtual Hosting with Nginx / Squid

Skitai doesn't support virtual hosting, and currently no plan to.

There're very wonderful tools like Nginx, Squid Server.


If you want 2 different and totaly unrelated websites:

- www.jeans.com
- www.carsales.com

And make two config in /etc/skitaid/servers-enabled

- jeans.conf *using port 5000*
- carsales.conf *using port 5001*

Then you can reverse proxying using Nginx, Squid or many others.

Example Squid config file (squid.conf) is like this:
    
    http_port 80 accel defaultsite=www.carsales.com
    
    cache_peer 192.168.1.100 parent 5000 0 no-query originserver name=jeans    
    acl jeans-domain dstdomain www.jeans.com
    http_access allow jeans-domain
    cache_peer_access jeans allow jeans-domain
    
    cache_peer 192.168.1.100 parent 5001 0 no-query originserver name=carsales
    acl carsales-domain dstdomain www.carsales.com
    http_access allow carsales-domain
    cache_peer_access carsales allow carsales-domain

For Nginx might be 2 config files (I'm not sure):

    ; /etc/nginx/sites-enabled/jean.com
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
    
### Developing and Deploying Process

### Specification of 'was'

#### Request Objects
##### was.app
##### was.request
##### was.cookie
##### was.session
##### was.env

#### View Server Status
##### was.status()
##### was.shutdown()
##### was.restart()
    
#### Object Serialize
##### was.tojson ()
##### was.toxml()

#### Asynchronous Network Related Services
##### was.wget()
##### was.map()
##### was.lb()
##### was.db()
##### was.dmap()
##### was.dlb()

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

### Use Cases











