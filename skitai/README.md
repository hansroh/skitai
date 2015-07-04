# Skitai App Engine Library

Skitai App Engine Library (SAEL) is a kind of branch of [Medusa Web Server](http://www.nightmare.com/medusa/medusa.html) - A High-Performance Internet Server Architecture.

Medusa is different from most other servers because it runs as a single process, multiplexing I/O with its various client and server connections within a single process/thread.

SAEL orients light-weight,simplicity  and strengthen networking operations with external resources - HTTP / HTTPS / RPC / [PostgreSQL](http://www.postgresql.org/) - keeping low costs.

It also influenced by [Zope](http://www.zope.org) and [Flask](http://flask.pocoo.org) a lot.

- It can be run as XML/JSON-RPC, Web and Proxy & Loadbancing Server.
- It can request massive RPC/HTTP(S) connections based on asynchronous socket framework at your apps easily.
- It provides asynchronous PostgreSQL query execution

Skitai is not a framework for combinient developing, module reusability and plugin flexibility etc. It just provides some powerful communicating services for your apps as both server and client.

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

### Hello World

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

### App For XML-RPC Map-Reduce

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

### App For PostgreSQL Map-Reduce

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

### Requirements

*Currently tested only in Python 2.7*

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

In your install dir (ex: .venv/lib/python27/site-packages/skitai)

copy all files from implements/sktaid to any location you want 

like /home/skitaid, c:\skitaid

    cp -rf .venv/lib/python27/site-packages/skitai/implements/skitaid /home/
    
    sudo mv /home/skitaid/etc/skitaid /etc/ (On Win32 move to c:\etc\)
    
### Configure Skitaid

Review and edit: 

**/etc/skitaid/skitaid.conf**

    [global]
    home = /home/skitaid
    
    ; location to save logs, locks, cache files
    var_path = /home/var
    
    ; python path
    ; on windows can like c:\python27]python.exe        
    python = python


**/etc/skitaid/servers-enabled/sample.conf**


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
    
    ; SESSION Cookie EN/DECRYPT KEY
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

Especially, You should change 

    securekey= 
    
This value is used to encrypting session values, so change very random string.

processes and threads value is usally recommended, 

    processes = [number of CPUs]
    threads = 4

* _Note 1: Threads value is per one process_

* _Note 2: On win32 processes should be '1'. I don't know how to create multi-workers at win32._



### Startup Skitaid

#### Run in console output for develop or debug

    cd /home/skitaid/bin
    python server.py -c -f sample

or silent run

    python server.py -f sample &
    
For more detail switch,

    python server.py --help

Then go to http://127.0.0.1:5000/ using your web browser


#### Run as Service

There's two scripts for starting Skitaid server.

bin/skitaid.py will start multiple server instances in all /etc/skitaid/servers-enabled directory.

bin/server.py will start single server instance by command line switch -f [config file name (do not write .conf)]

Here's some example for running skitaid.py as service.

##### Liunx
Edit example script under skitaid/etc/init (Ubuntu) & init.d (CentOS)

then copy /etc/init or /etc/init.d by your OS env.

##### Win32

Go to skitaid/bin/win32service

    install_win32_service.py --startup auto install


### Shutdown Skitaid

If you start with server.py, Ctrl-C is good.

else if run with skitaid.py

    python skitaid.py stop

or restarting sample.conf server,
    
    python skitaid.py -k restart -n sample

for more detail switch, 

    python skitaid.py --help

if runnig as service on posix,

    sudo skitaid stop
    or
    sudo service skitaid stop

in win32, control Service contrl Manager
  



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

You can access, 

    http://127.0.0.1:5000/test/


### Routing

If you configure,
                
    /test = /home/skitaid/app/webapp

/test/ is working like directory, but /test is like file.

It makes somewhat differnces inner 'a href' links.

    /test = /home/skitaid/app/test
    /test = /home/skitaid/app/webapp
    
It's a little confused, but is not.

Above /home/skitaid/app/test is directory, and the below /home/skitaid/app/webapp is webapp.py module.

So Skitaid find first /home/skitaid/app/test/index.htm (or index.html).

If not exists, find method of /home/skitaid/app/webapp.py.

Bottom line, always psysical directory/file has priority.

    @app.route ("/hello/world")
    def wget (was, url):
        return "Hello"

/test is base path for /home/skitaid/app/webapp, then fully translated to:

    http://127.0.0.1:5000/test/hello/world
    
    or as XML-RPC,    
    
    s.test.hello.world ()
    

        
### Set App Development Mode
    
    app.set_devel (True)

If this is not set True, This app will be never reloaded whether you modify webapp.py or not.

At real service situation, it would be  False for better perfomance, and False is default.

    
### What is 'was'?

All app method's 1st arg is 'was'.

    def wget (was, url):
        return "Hello"
        
'was' is similar to 'self' in class instance method.

Imagine your app methods is App Server Class' methods.

'was` provide some objects related with request:
    
- was.request
- was.response
- was.cookie
- was.session
- was.env
  
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
        
    @package.route ("/greetings/morning")
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

This means when app is initailizing, add greetings sub-package.

Sub-package inherit app's devel mode, base routing path and Jinja2 template pathes etc.

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


### More About App Contructor, Reconstructor and Deconstructor (App CRD)

It's useful, some object should be alive with app engine's lifetime and need to share with all the other apps.
    
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
        # re-setting
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
    
    # header lines list
    was.request.get_headers ()
    
    path, param, querystring, fragment =  was.request.split_uri ()
    
    # get/head/post/put ...
    was.request.command
    
    # HTTP version
    was.request.version
    
    was.request.uri
    
    was.request.get_content_type ()
    
    was.request.get_main_type ()
    
    was.request.get_sub_type ()
    
    was.request.get_remote_addr ()
    
    was.request.get_user_agent ()    
    
    # access raw form or multipart data (if size <= 5MB)
    was.request.get_body ()
    

### Reponse Handling
      
Response example:
    
    was.response.reply (301, "Object Moved")
    was.response ["Location"] = "/newloc"    
    return ""

Header setting:

    was.response ["Location"] = "/newloc"
    
    del was.response ["Location"]

    was.response.has_key ("Content-Type")
    
    was.response.set ("Location", "/newloc")
    
    ; modify existing header, if not exists, will be created.
    was.response.update ("Content-Transfer-Encoding", "gzip")
    
    was.response.delete ("Content-Length")
    
**Note**: Header key allowed duplication. So you intent to set only one unique header, DO NOT use *was.response [KEY]=VALUE* or *was.response.set(KEY, VALUE)*, but USE *was.response.update(KEY, VALUE)*

Example for check request method:

    if was.request.command == "get":
      was.response.reply (405, "Method Not Allowed")
      return "Not allowed get method for %s" % was.request.uri

More simply:

    if was.request.command == "get":
      return was.response.error (405)
      
Example for bang for specipic IP Address:
    
    if was.request.get_remote_addr ().startswith ("192.168.1."):
      return was.response.abort (403)
      

*NOTE:* It's not necessary call was.response.reply (200, "OK") if every thing OK, just return result.

#### Detail about Return Value Type

Retrun value should be some types by cases.

**For Web Service**

- any string type like HTML, binary data of file or serialized string by was.tojson () or was.toxml()
- class has 'more()' method for streaming

**For XML/JSON-RPC**

- Any object allowed by each RPC specification
- **Not allowed** for streaming class

Actually, you can serve any of them in one method.

    @app.route ("/multi_purpose")
    def multi_purpose (was):
      ct = was.reuqest.get_header ("content-type")
      if ct is not None and ct.startswith ("application/json-rpc") or ct.startswith ("text/xml"):
         return OBJECT
      else:
         return was.app.get_template ("multi_purpose.html").render (OBJECT)
         

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



### Getting ARGS

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

Actually, can be mixed with theses 3 methods.

It means also possible:

    @app.route ("/company/<int:cid>")
    def company (was, cid, cname):
      return "%d - %s" % (cid, cname)

     http://127.0.0.1:5000/company/555&cname=Skitai+Corp

 If args' name is duplicated like this: 
 
     http://127.0.0.1:5000/company/555&cname=Skitai+Corp&cid=333
 
Var name 'cid' will be convert to list **["333", 555]**.

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
        else:
          return "Error"
          
form-data post request,
     
     s = was.wget (url, {"cid": "555", "cname="Skitai Corp"})
     
 
 multipart file upload request,
 
     s = was.wget (
     	url, 
     	{"cid": "555", "cname="Skitai Corp", "file": open ("/data/logo.gif")}, 
     	multipart = True    
     )
    
 RPC request
    
    @app.route ("/test/rpc")
    def rpc (was):
        s = was.rpc ("https://www.python.org/rpc2")
        s.query ( "Beethoven")
        return s.getwait (timeout = 2)


### RPC Map-Filter-Reduce (MFR) Operation
 
 At first, you configure members like this:   
    
    [@myrpcs]
    ssl = yes
    members = s1.yourserver.com:5000,s2.yourserver.com:5000,s3.yourserver.com:5000

Then you can MFR operation using 'myrpcs'.

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
    
- getswait(timeout) used for multiple results returned from was.map(), was.dmap()
    
- getwait(timeout) used for a result returned from was.lb(), was.dlb(), was.db(), was.wget()
    
    
    
### RPC Load-Balacing

You an load balncing to configures members with was.lb ():

At config file:

    [@myrpcs]
    ssl = no
    members = s1.yourserver.com:5000,s2.yourserver.com:5000,s3.yourserver.com:5000

Your app is:

    @app.route ("/search")
    def search (was, keyword = "Mozart"):
      s = was.lb ("myrpcs/rpc2")
      s.search (keyword)
      return s.getwait (timeout = 2)


### Connect to PostgreSQL

First of all you should know, there're some limitations in asynchronous query execution mode.

> There are several limitations in using asynchronous connections: the connection is always in autocommit mode and it is not possible to change it. So a transaction is not implicitly started at the first query and is not possible to use methods commit() and rollback(): you can manually control transactions using execute() to send database commands such as BEGIN, COMMIT and ROLLBACK. Similarly set_session() can¡¯t be used but it is still possible to invoke the SET command with the proper default_transaction_... parameter.

> With asynchronous connections it is also not possible to use set_client_encoding(), executemany(), large objects, named cursors.

> COPY commands are not supported either in asynchronous mode, but this will be probably implemented in a future release.

> From http://initd.org/psycopg/docs/advanced.html

    @app.route ("/test/db")
    def db (was):
    	s = was.db ("127.0.0.1:5432", "mydb", "postgres", "password")
    	s.execute ("SELECT * FROM weather;")
    	rs = s.getwait (2)    	
    	return rs.data [0:10]

There're no was.db.close (), db connections are managed by was' db pool. Just query and use result.

### PostgreSQL Map-Filter-Reduce (MFR) Operation
 
At first, you configure members like this:   
    
    [@mydbs]
    type = posgresql    
    members = s1.yourserver.com:5432/mydb/user/pass,s2.yourserver.com:5432/mydb/user/pass

Then you can MFR operation using 'mydbs'.

First example is simple Map-Reduce for getting top population city:

    @app.route ("/test/get_top_city")
    def get_top_city (was):
    
        s = was.dmap ("mydbs")
         
        # we expect [{"name": "Fairfax", "population": 23478}, ...]
        s.execute ("SELECT name, population from CITIES;")
        
        all = []
        for rs in s.getswait (5):
            if rs.status != 3: continue
            all.extend ([(each ["city"], each ["population"]) for each in rs.data])
            
        all.sort (lambda x, y: cmp (y [1], x [1]))
        return all [0]
    
And inspite of foolish, here's Map-Filter-Reduce example:

    @app.route ("/test/get_top_city")
    def get_top_city (was):      
      
        def remove_too_little (rs):
          if rs.status == 3:
          	rs.data =  filter (lambda x: x ["population"] >= 100000, rs.data)          	
          else:
            rs.data = []
            
        s = was.dmap ("mydbs", filter = remove_too_little)    
        s.execute ("SELECT name, population from CITIES;")
        
        all = []
        for rs in s.getswait (5):
            all.extend ([(each ["city"],each ["population"]) for each in rs.data])
            
        all.sort (lambda x, y: cmp (y [1], x [1]))
        return all [0]
 
    
### PostgreSQL Load-Balacing

Same config file, and your app is:

    s = was.dlb ("mydbs")    
    s.execute ("SELECT name, population from CITIES;")
    return s.getwait (2)
    
      
### RPC/PosgreSQL Caching

At config, 

    num_result_cache_max = 2000
    
means  maximum number of  RPC/PosgreSQL results

    s = was.dlb ("mydbs")    
    s.execute ("SELECT name, population from CITIES;")
    result =  s.getwait (2)
    
    # cache for 300 sec.
    result.cache (timeout = 300)

    s = was.map ("myrpcs/rpc2")    
    s.generate_random_int_list (5)
    results = s.getswait (5):
    
    # cache for 60 sec.
    results.cache (timeout = 60)

    
### Rendering HTML with Jinja2 Template

Directory structure is like this:

    /home/skitaid/app/webapp.py
                     /static
                     /tempates/index.html
    
Now you can get_template ():
    from skitai.server import ssgi
    app = ssgi.Application (__name__)
    
    @app.route ("/")
    def main (was):
        template = was.app.get_template ('index.html')
        
        d = {"url": urllib.quote ("https://pypi.python.org/pypi")}
        return template.render (d)
    
    
### Cookie & Session

For using session, should be enabled first,

    app = ssgi.Application (__name__)
    app.set_devel (True)
    app.use_session (True)

Sign In:

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
 
Session is encrypted cookie, and this idea and source code came from Flask.

    
### Automatic Call Before, After and Teardown Request (BAT)

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

Now, automatically called BAT functions in all app's method.
    
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
        send (response)
        return
    
    try:
      response = myorder(was)
    
    except:
      if teardown_request:
        response = teardown_request(was)
        
      else:
        send 500 error
        return
    
    send (response)
    

Also ssgi.package can have BAT.

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

For more detail, see *Building Larger App* section again.

            
### Streaming Response
  
 You can return large data, but might be occured some problems - long response time, and occupying thread.
 
 So you can make class has method 'more' and optional 'abort':
    
    @app.route ("/streaming")
    def Stream (was, filename):
      class Stream:
        def __init__ (self, filename):          
          self.f = open (filename, "rb")
        
        def close (self):
          self.f.close ()
        
        def abort (self): 
          # it will be called client channel is suddenly disconnected
          self.close ()
            
        def more (self):
          data = self.f.read (4096)
          if not data:
          	self.close ()
          return data
      
      was.response ["Content-Type"] = "video/mp4"
      was.response ["Cache-Control"] = "max-age=3600"
      
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
        karg.get ("submit-hidden")
        karg.get ("file") ["mimetype"]
        
karg is like this:
    
    krgs = {
    'submit-hidden': 'Hans Roh', 
    'file': {'mimetype': 'application/octet-stream', 'local': '/tmp/tmposndlr', 'remote': 'study.sql', 'size': 511}
    }

        

### Load-Balancing Reverse Proxy For WEB / RPC

Your congig file:
    
    [routes:line]
    /articles = @mywebservers
    
    [@mywebservers]
    ssl = no
    members = 192.168.1.100:5000,192.168.1.101:5000,192.168.1.102:5000 
    
You can call like this,

    http://127.0.0.1/articles/view?id=555



### (Forward) Proxy

Proxy is maden for experimental purpose, so be careful for open.

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
    
For generating certfile an cafile using openSSL, see 

    /etc/skitaid/cert/generate/README.txt
    


### Virtual Hosting with Nginx / Squid

Skitai doesn't support virtual hosting, and currently no plan to for keeping simplicity.

Another reason, there're very wonderful servers for this like Nginx, Squid.


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


### Developing and Deploy

#### Coding

The most important thing is, RPC/DB requests should be positioned top of the method as possible for background execution, then do antother jobs you need in the middle of code. 

Finally call getswait(timeout) / getwait(timeout) and use the result.

It's the way for getting maximum speed and benefit from Skitai framework.

#### Propose 2 Server System

I'm not sure the most efficient process for developing & deploying yet.

Currently I suggest like this,

**Directory structure**

    /home/apps/project1/deploy/webapp.py
                              /static
                              /tempaltes
                              /packages

                       /sandbox/webapp.py
                               /static
                               /tempaltes
                               /packages

Application automatically set_devel (True) mode, if detected app's path contains 'sandbox'

Then if done developing just copy to deploy, and restart deploy server.

And need 2 configure files:

    project1.conf in /etc/skitaid/servers-enabled/
   
    sandbox.conf in /etc/skitaid/servers-available/
   
project1.conf will be runs as service with system starting.

sandbox.conf can be run in console with outputing debug msg and viewing error msg.

    python server.py -c -f a/sandbox

'a/sandbox' means '/etc/skitaid/servers-available/sandbox.conf'

If you multiple webservers for loadbalancing/clustering, also can make network deploying app your own with using Skitais's powerful and simple communicating capability, or might be added to Skitai 'was' methods as basic service later.


### Specification of 'was'

#### Request Objects

These object is already explained above.

- was.app
- was.request
- was.response
- was.cookie
- was.session
- was.env


#### Asynchronous Network Related Services

For HTTP / HTTPS / RPC

- was.wget() : On-Demand connection managed by socket pool

    wget (uri, params = None, login = None, encoding = None, multipart = False, filter = None)
    
- was.map() : Map-Filter-Reducing
    
    map (clustername, params = None, login = None, encoding = None, multipart = False, filter = None)

- was.lb() : Load Bancing

    lb (clustername, params = None, login = None, encoding = None, multipart = False, filter = None)
   
For PostgreSQL

- was.db() : On-Demand connection managed by db connection pool
    
    db (server, dbname, user, password, dbtype = "postgresql", filter = None)    

- was.dmap() : Map-Filter-Reducing

    dmap (self, clustername, filter = None)
       
- was.dlb() : Load Bancing

    dlb (self, clustername, filter = None)

#### Server Status

This methods is reliable when run with single process for app development. 

But in multi processes, don't believe most all nuber and objects status.

- was.status()

Display all server components has status () method.

    * was.apps
    * was.cachefs
    * was.rcache
    * was.httpserver
    * was.lifetime
    * was.queue
    * was.threads
    * was.cluster[socketpool]
    * was.cluster[dbpool]
    * was.cluster[@user-configured-clusters]
    * was.[user-registered-objects]

These are applied only current sample.conf instance worker. also for developing aid.

- was.shutdown()
- was.restart()
    

#### Object Serialize

- was.tojson ()
- was.toxml(): to XMLRPC

