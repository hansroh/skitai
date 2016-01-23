Skitai WSGI App Engine
==========================

Copyright (c) 2015 by Hans Roh

License: BSD



What's New
-----------

Newly added 3 Skitai 'was' client-side web socket services:

- was.ws ()
- was.ws.lb ()
- was.ws.map ()

It is desinged as simple & stateless request-response model using web socket message frame for *light overheaded server-to-server communication*. For example, if your web server queries to so many other search servers via RESTful access, web socket might be a good alterative option. Think HTTP-Headerless JSON messaging. Usage is very simailar with HTTP request.

.. code:: python

  @app.route ("/query")
  def query (was):
    s = was.ws (
    	"ws://192.168.1.100:5000/websocket/echo", 
    	json.dumps ({"keyword": "snowboard binding"})
    )
    rs = s.getwait ()
    result = json.loads (rs.data)

Obiously, target server should have Web Socket app, routed to '/websocket/echo' in this case.

To build WSGI application can handle web sockets on Skitai, see *HTML5 Web Socket* section.

	  
Introduce
----------

Skitai App Engine (SAE) is a kind of branch of `Medusa Web Server`__ - A High-Performance Internet Server Architecture.

Medusa is different from most other servers because it runs as a single process, multiplexing I/O with its various client and server connections within a single process/thread.

SAE orients light-weight, simplicity  and strengthen networking operations with external resources - HTTP / HTTPS / XML-RPC / PostgreSQL_ - keeping very low costs.

It is influenced by Zope_ and Flask_ a lot.

- SAE can be run as Web, XML-RPC and Reverse Proxy Loadbancing Server
- SAE can handle massive RESTful API/RPC/HTTP(S) connections based on asynchronous socket framework at your apps easily
- SAE provides asynchronous connection to PostgreSQL

Skitai is not a framework for convinient developing, module reusability and plugin flexibility etc. It just provides some powerful communicating services for your WSGI apps as both server and client.

From version 0.10, Skitai App Engine follows WSGI specification. So existing Skitai apps need to lots of modifications.

Conceptually, SAE has been seperated into two components:

1. Skitai App Engine Server, for WSGI apps

2. Saddle, the small WSGI middleware integrated with SAE. But you can also mount any WSGI apps and frameworks like Flask.


.. _Zope: http://www.zope.org/
.. _Flask: http://flask.pocoo.org/
.. _PostgreSQL: http://www.postgresql.org/
.. __: http://www.nightmare.com/medusa/medusa.html



Mounting WSGI Apps
--------------------

Here's three WSGI app samples:

*WSGI App* at /var/wsgi/wsgiapp.py

.. code:: python
  
  def app (env, start_response):
    start_response ("200 OK", [("Content-Type", "text/plain")])
    return ['Hello World']


*Flask App* at /var/wsgi/flaskapp.py

.. code:: python

  from flask import Flask  
  app = Flask(__name__)  
  
  @app.route("/")
  def index ():	 
    return "Hello World"


*Skitai-Saddle App* at /var/wsgi/skitaiapp.py

.. code:: python

  from skitai.saddle import Saddle  
  app = Saddle (__name__)
  
  @app.route('/')
  def index (was):	 
    return "Hello World"

For mounting to SAE, modify config file in /etc/skitaid/servers-enabled/sample.conf

.. code:: python
  
  [routes:line]
  
  ; for files like images, css
  / = /var/wsgi/static
  
  ; app mount syntax is path/module:callable
  / = /var/wsgi/wsgiapp:app
  /aboutus = /var/wsgi/flaskapp:app
  /services = /var/wsgi/skitaiapp:app
  
You can access Flask app from http://127.0.0.1:5000/aboutus and other apps are same.


**Note: Mount point & App routing**

If app is mounted to '/flaskapp',

.. code:: python
   
  from flask import Flask    
  app = Flask (__name__)       
  
  @app.route ("/hello")
  def hello ():
    return "Hello"

Above /hello can called, http://127.0.0.1:5000/flaskapp/hello

Also app should can handle mount point. 
In case Flask, it seems 'url_for' generate url by joining with env["SCRIPT_NAME"] and route point, so it's not problem. Skitai-Saddle can handle obiously. But I don't know other WSGI middle wares will work properly.


Virtual Hosting
-------------------

.. code:: python

  [routes:line]
  
  : default  
  / = /home/user/www
  
  ; exactly matching host
  : www.mydomain.com mydomain.com  
  / = home/user/mydomain.www
  
  ; matched *.mydomain.com
  : .mydomain.com
  / = home/user/mydomain.any 

`New in version 0.10.5`


*Note:* For virtual hosting using multiple Skitai instances with Nginx/Squid, see `Virtual Hosting with Nginx / Squid` at end of this document.


Note For Python 3 Users
-------------------------

**Posix**

SAE will be executed with /usr/bin/python (mostly symbolic link for /usr/bin/python2).

For using Python 3.x, change skitaid scripts' - /usr/local/bin/sktaid*.py - first line from `#!/usr/bin/python` to `#!/usr/bin/python3`. Once you change, it will be kept, even upgrade or re-install skitai.

In this case, you should re-install skitai and requirements using 'pip3 install ...'.


**Win32**

Change python key value to like `c:\python34\python.exe` in c:\skitaid\etc\skitaid.conf.


Asynchronous Requests Using Skitai WAS
-----------------------------------------

'WAS' means (Skitai) *WSGI Application Service*.

**Simple HTTP Request**

*Flask Style:*

.. code:: python

  from flask import Flask, request
  from skitai import was
  
  app = Flask (__name__)        
  @app.route ("/get")
  def get ():
    url = request.args.get('url', 'http://www.python.org')
    s = was.get (url)
    result = s.getwait (5) # timeout
    return result.data


*Skitai-Saddle Style*

.. code:: python

  from skitai.saddle import Saddle
  app = Saddle (__name__)
        
  @app.route ("/get")
  def get (was, url = "http://www.python.org"):
    s = was.get (url)
    result = s.getwait (5) # timeout
    return result.data

Both can access to http://127.0.0.1:5000/get?url=https%3A//pypi.python.org/pypi .

If you are familar to Flask then use it, otherwise choose any WSGI middle ware you like include Skitai-Saddle.

Also note that if you want to use WAS services in your WSGI middle wares except Skitai-Saddle, you should import was.

.. code:: python

  from skitai import was


Here're post, file upload method examples:

.. code:: python

  s1 = was.post (url, {"user": "Hans Roh", "comment": "Hello"})
  s2 = was.upload (url, {"user": "Hans Roh", "file": open (r"logo.png", "rb")})
  
  result = s1.getwait (5)
  result = s2.getwait (5)


Here's XMLRPC request for example:

.. code:: python

  s = was.rpc (url)
  s.get_prime_number_gt (10000)
  result = s.getwait (5)


Avaliable methods are:

- was.get (url, auth = (username, password))
- was.post (url, data = data, auth = (username, password))
- was.rpc (url, auth = (username, password)) # XMLRPC
- was.ws (url, data, auth = (username, password)) # Web Socket
- was.put (url, data = data, auth = (username, password))
- was.delete (url)
- was.upload (url, data, auth = (username, password)) # For clarity to multipart POST


**Load-Balancing**

If server members are pre defined, skitai choose one automatically per each request supporting *fail-over*.

At first, let's add mysearch members to config file (ex. /etc/skitaid/servers-enabled/sample.conf),

.. code:: python

  [@mysearch]
  ssl = yes
  members = search1.mayserver.com:443, search2.mayserver.com:443
    

Then let's request XMLRPC result to one of mysearch members.
   
.. code:: python

  @app.route ("/search")
  def search (was, keyword = "Mozart"):
    s = was.rpc.lb ("@mysearch/rpc2")
    s.search (keyword)
    results = s.getwait (5)
    return result.data

It just small change from was.rpc () to was.rpc.lb ()

Avaliable methods are:

- was.get.lb ()
- was.post.lb ()
- was.rpc.lb ()
- was.ws.lb ()
- was.upload.lb ()
- was.put.lb ()
- was.delete.lb ()


*Note:* If @mysearch member is only one, was.get.lb ("@mydb") is equal to was.get ("@mydb").

*Note2:* You can mount cluster @mysearch to specific path as proxypass like this:

At config file

.. code:: python
  
  [routes:line]  
  ; for files like images, css
  / = /var/wsgi/static
  
  ; app mount syntax is path/module:callable
  /search = @mysearch  
  
It can be accessed from http://127.0.0.1:5000/search, and handled as load-balanced proxypass.

  

**Map-Reducing**

Basically same with load_balancing except SAE requests to all members per each request.

.. code:: python

    @app.route ("/search")
    def search (was, keyword = "Mozart"):
      s = was.rpc.map ("@mysearch/rpc2")
      s.search (keyword)
      results = s.getswait (2)
			
      all_results = []
      for result in results:
         all_results.extend (result.data)
      return all_results

There are 2 changes:

1. from was.rpc.lb () to was.rpc.map ()
2. form s.getwait () to s.getswait () for multiple results

Avaliable methods are:

- was.get.map ()
- was.post.map ()
- was.rpc.map ()
- was.ws.map ()
- was.upload.map ()
- was.put.map ()
- was.delete.map ()


**PostgreSQL Map-Reducing**

This sample is to show querying sharded database.
Add mydb members to config file.

.. code:: python

    [@mydb]
    type = postresql
    members = s1.yourserver.com:5432/mydb/user/passwd, s2.yourserver.com:5432/mydb/user/passwd


.. code:: python

    @app.route ("/query")
    def query (was, keyword):
      s = was.db.map ("@mydb")
      s.execute("SELECT * FROM CITIES;")

      results = s.getswait (timeout = 2)
      all_results = []
      for result in results:
        if result.status == 3:
          all_results.append (result.data)
      return all_results


Basically same usage concept with above HTTP Requests.

Avaliable methods are:

- was.db ("127.0.0.1:5432", "mydb", "postgres", "password")
- was.db ("@mydb")
- was.db.lb ("@mydb")
- was.db.map ("@mydb")

*Note:* if @mydb member is only one, was.db.lb ("@mydb") is equal to was.db ("@mydb").


**Sending e-Mails**

.. code:: python

    # email delivery service
    e = was.email (subject, snd, rcpt)
    e.set_smtp ("127.0.0.1:465", "username", "password", ssl = True)
    e.add_text ("Hello World<div><img src='cid:ID_A'></div>", "text/html")
    e.add_attachment (r"001.png", cid="ID_A")
    e.send ()

With asynchronous email delivery service, can add default SMTP Server config to skitaid.conf (/etc/skitaid/skitaid.conf or c:\skitaid\etc\skitaid.conf).
If it is configured, you can skip e.set_smtp(). But be careful for keeping your smtp password.

.. code:: python

    [smtpda]
    smtpserver = 127.0.0.1:25
    user = 
    password = 
    ssl = no
    max_retry = 10
    undelivers_keep_max_days = 30


**Other Utility Service**

- was.status ()
- was.tojson ()
- was.fromjson ()
- was.toxml () # XMLRPC
- was.fromxml () # XMLRPC



HTML5 Web Socket
--------------------------------------

*New in version 0.11*


Mendtioned above, there're 3 Skitai 'was' client-side web socket services:

- was.ws ()
- was.ws.lb ()
- was.ws.map ()

It is desinged as simple & no stateless request-response model using web socket message frame for *light overheaded server-to-server communication*. For example, if your web server queries to so many other search servers via RESTful access, web socket might be a good alterative option. Think HTTP-Headerless JSON messaging. Usage is very simailar with HTTP request.

.. code:: python

  @app.route ("/query")
  def query (was):
    s = was.ws (
    	"ws://192.168.1.100:5000/websocket/echo", 
    	json.dumps ({"keyword": "snowboard binding"})
    )
    rs = s.getwait ()
    result = json.loads (rs.data)
	  
Obiously, target server should have Web Socket app, routed to '/websocket/echo' in this case.



Also at server-side, HTML5 Web Socket has been implemented obioulsy

But I'm not sure my implemetation is right way, so it is experimental and unstatable.

I think there're 3 handling ways to use websockets.

1. thread pool manages n websocket connection

2. one thread per websocket connection

3. one thread manages n websockets connection

So skitai supports above all 3 ways.

First of all, see conceptual client side java script for websocket.

.. code:: html

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
  function onClose(evt) {writeToScreen("DISCONNECTED");}  
  function onMessage(evt) {writeToScreen('<span style="color: blue;">RESPONSE: ' + evt.data+'</span>');}
  function onError(evt) {writeToScreen('<span style="color: red;">ERROR:</span> ' + evt.data);}  
  function doClose () {websocket.close();}  
  function doSend(message) {websocket.send(message);}
  </script>


If your WSGI app enable handle websocket, it should give  initial parameters to Skitai.

You should check exist of env ["websocket_init"], set initializing parameters.

initializing parameters should be tuple of (websocket design spec, keep alive timeout, variable name)

*websocket design specs* can  be choosen one of 3 .

WEBSOCKET_REQDATA

  - Thread pool manages n websocket connection
  - It's simple request and response way like AJAX
  - Use skitai initail thread pool, no additional thread created
  - Low cost on threads resources, but reposne cost is relatvley high than the others
  
WEBSOCKET_DEDICATE

  - One thread per websocket connection
  - Use when reponse maiking is heavy and takes long time
  - New thread created per websocket connection
  
WEBSOCKET_MULTICAST
  
  - One thread manages n websockets connection
  - Chat room model, all websockets will be managed by single thread
  - New thread created per chat room

*keep alive timeout* is seconds.

*variable name* is various usage per each design spec.


**WEBSOCKET_REQDATA**

Here's a echo app for showing simple request-respone.

Client can connect by ws://localhost:5000/websocket/chat.

*Skitai-Saddle Style*

.. code:: python

  from skitai.saddle import Saddle
  import skitai
  
  app = Saddle (__name__)
  app.debug = True
  app.use_reloader = True

  @app.route ("/websocket/echo")
  def echo (was, message = ""):
    if "websocket_init" in was.env:
      was.env ["websocket_init"] = (skitai.WEBSOCKET_REQDATA, 60, "message")
      return ""
    return "ECHO:" + message

*Flask Style*

.. code:: python

  from flask import Flask, request 
  import skitai
  
  app = Flask (__name__)
  app.debug = True
  app.use_reloader = True

  @app.route ("/websocket/echo")
  def echo ():
    if "websocket_init" in request.environ:
      request.environ ["websocket_init"] = (skitai.WEBSOCKET_REQDATA, 60, "message")
      return ""
    return "ECHO:" + request.args.get ("message")

In this case, variable name is "message", It means take websocket's message as "message" arg.


**WEBSOCKET_DEDICATE**

This app will handle only one websocket client. and if new websocekt connected, will be created new thread.

Client can connect by ws://localhost:5000/websocket/talk?name=Member.

.. code:: python

  @app.route ("/websocket/talk")
  def talk (was, name):
    if "websocket_init" in was.env:
      was.env ["websocket_init"] = (skitai.WEBSOCKET_DEDICATE, 60, None)
      return ""
    
    ws = was.env ["websocket"]
    while 1:
      messages = ws.getswait (10)
      if messages is None:
        break  
      for m in messages:
        if m.lower () == "bye":
          ws.send ("Bye, have a nice day." + m)
          ws.close ()
          break
        elif m.lower () == "hello":
          ws.send ("Hello, " + name)        
        else:  
          ws.send ("You Said:" + m)

In this case, variable name should be None. If exists, will be ignored.


**WEBSOCKET_MULTICAST**

Here's simple mutiuser chatting app.

Many clients can connect by ws://localhost:5000/websocket/chat?roomid=1. and can chat between all clients.

.. code:: python

  @app.route ("/websocket/chat")
  def chat (was, roomid):
    if "websocket_init" in was.env:
      was.env ["websocket_init"] = (skitai.WEBSOCKET_MULTICAST, 60, "roomid")
      return ""
    
    ws = was.env ["websocket"]  
    while 1:
      messages = ws.getswait (10)
      if messages is None:
        break  
      for client_id, m in messages:
        ws.sendall ("Client %d Said: %s" % (client_id, m))

In this case, variable name is "roomid", then Skitai will create websocket group seperatly.


You can access all examples by skitai sample app after installing skitai.

.. code:: python

  sudo skitaid-instance.py -v -f sample

Then goto http://localhost:5000/websocket in your browser.
    


Request Handling with Saddle
----------------------------

*Saddle* is WSGI middle ware integrated with Skitai App Engine.

Flask and other WSGI middle ware have their own way to handle request. So If you choose them, see their documentation. And note that below objects will *NOT* be avaliable on other WSGI middle wares.


**Debugging**

.. code:: python

  app = Saddle (__name__)
  app.debug = True # output exception information
  app.use_reloader = True # auto realod on file changed
  

For output message & error in console:  

*Posix*

sudo /usr/local/bin/skitai-instance.py -v -f sample
  

*Win32*

c:\skitaid\bin\skitai-instance.py -v -f sample


  
**Access Request**

.. code:: python

  was.request.get_header ("content-type") # case insensitive
  was.request.get_header () # retrun header all list
  was.request.command # lower case get, post, put, ...
  was.request.version # HTTP Version, 1.0, 1.1
  was.request.uri  
  was.request.get_body ()
  was.request.get_remote_addr ()
  was.request.get_user_agent ()


**Handle Response**

.. code:: python

  was.response ["Content-Type"] = "text/plain"
  was.response.set_status ("200 OK") # default value
  return "Hello"
    
  was.response.send_error ("500 Server Error", why = "It's not my fault")
  return "" # should null string/bytes after call send_error ()
  
  was.response ["Content-Type"] = "video/mp4"
  return open ("mypicnic.mp4", "rb")
  
  was.response ["Content-Type"] = "text/csv"  
  def generate():
    for row in iter_all_rows():
      yield ','.join(row) + '\n'  
  return generate()
  
Available return types are:

- String, Bytes, Unicode
- File-like object has 'read (buffer_size)' method, optional 'close ()'
- Iterator/Generator object has 'next() or _next()' method, optional 'close ()' and shoud raise StopIteration if no more data exists.
- Something object has 'more()' method, optional 'close ()'
- Classes of skitai.lib.producers
- List/Tuple contains above objects
- XMLRPC dumpable object for if you want to response to XMLRPC

The object has 'close ()' method, will be called when all data consumed, or socket is disconnected with client by any reasons.


**Getting URL Parameters**

.. code:: python
  
  @app.route ("/hello")
  def hello_world (was, num = 8):	
    return num
  # http://127.0.0.1:5000/hello?num=100
	
	
  @app.route ("/hello/<int:num>")
  def hello_world (was, num = 8):
    return str (num)
    # http://127.0.0.1:5000/hello/100


Available fancy URL param types:

- int
- float
- path: /download/<int:major_ver>/<path>, should be positioned at last like /download/1/version/1.1/win32
- If not provided, assume as string. and all space char replaced to "_'


**Getting Form Parameters**

.. code:: python

  @app.route ("/hello")
  def hello (was, **form):  	
  	return "Post %s %s" % (form.get ("userid", ""), form.get ("comment", ""))
  	
  @app.route ("/hello")
  def hello_world (was, userid, **form):
  	return "Post %s %s" % (userid, form.get ("comment", ""))

	
**File Upload**

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
			  
file object has these attributes:

- file.file: temporary saved file full path
- file.name: original file name posted
- file.size
- file.mimetype
- file.remove ()
- file.save (into, name = None, mkdir = False, dup = "u")
  * if name is None, used file.name
  * dup: 
    
    + u - make unique (default)
    + o - overwrite



**Access Environment Variables**

.. code:: python

  was.env.keys ()
  was.env.get ("CONTENT_TYPE")


**Access App & Jinja Templates**

.. code:: python

  if was.app.debug:
    was.app.get_template ("index-debug.html") # getting Jinja template
  else:  
    was.app.get_template ("index.html") # getting Jinja template

Directory structure sould be:

- app.py
- templates/index.html


**Access Cookie**

.. code:: python

  if was.cookie.get ("user_id") is None:
  	was.cookie.set ("user_id", "hansroh")
  	
- was.cookie.set (key, val)
- was.cookie.get (key)
- was.cookie.remove (key)
- was.cookie.clear ()
- was.cookie.kyes ()
- was.cookie.values ()
- was.cookie.items ()


**Access Session**

To enable session for app, random string formatted securekey should be set for encrypt/decrypt session values.

*WARN*: `securekey` should be same on all skitai apps at least within a virtual hosing group, Otherwise it will be serious disater.

.. code:: python

  app.securekey = "ds8fdsflksdjf9879dsf;?<>Asda"
  app.session_timeout = 1200 # sec
  
  @app.route ("/session")
  def hello_world (was, **form):  
    if was.session.get ("login") is None:
      was.session.set ("user_id", form.get ("hansroh"))
  
- was.session.set (key, val)
- was.session.get (key)
- was.session.remove (key)
- was.session.clear ()
- was.session.kyes ()
- was.session.values ()
- was.session.items ()


**Building URL**

.. code:: python

  @app.route ("/add")
  def add (was, num1, num2):  
    return int (num1) + int (num2)
    
  was.app.build_url ("add", 10, 40) # returned '/add?num1=10&num2=40'
  # BUT it's too long to use practically,
  # was.ab is acronym for was.app.build_url
  was.ab ("add", 10, 40) # returned '/add?num1=10&num2=40'
  was.ab ("add", 10, num2=60) # returned '/add?num1=10&num2=60'
  
  @app.route ("/hello/<name>")
  def hello (was, name = "Hans Roh"):
    return "Hello, %s" % name
	
  was.ab ("hello", "Your Name") # returned '/hello/Your_Name'


**Chained Execution**

.. code:: python

  @app.before_request
  def before_request (was):
    if not login ():
      return "Not Authorized"
  
  @app.after_request
  def after_request (was):
    was.temp.user_id    
    was.temp.user_status
    ...
  
  @app.failed_request
  def failed_request (was):
    was.temp.user_id    
    was.temp.user_status
    ...
  
  @app.teardown_request
  def teardown_request (was):
    was.temp.resouce.close ()
    ...
  
  @app.route ("/view-account")
  def view_account (was, userid):
    was.temp.user_id = "jerry"
    was.temp.user_status = "active"
    was.temp.resouce = open ()
    return ...


For this situation, 'was' provide was.temp that is empty class instance. was.temp is valid only in cuurent request. After end of current request, was.temp is reset to empty.


If view_account is called, Saddle execute these sequence:

.. code:: python
  
  try:
    try: 
      content = before_request (was)
      if content: 
        return content
      content = view_account (was, *args, **karg)
    except:
      failed_request (was)
    else:
      after_request (was)
  finally:
    teardown_request (was)
    

Also it is possible to bind some events with temporary handling methods.

.. code:: python

  from skitai.saddle import EVOK, EVEXCEPT, EVREQEND
  
  @app.route ("/view-account")

  def view_account (was, userid):
    def handle_ok (was):
    	was.temp.user_id
    	was.temp.user_status
    
    was.temp.bind (EVOK, handle_ok)
    was.temp.bind (EVEXCEPT, handle_except)
    was.temp.bind (EVREQEND, handle_end)
   
    was.temp.user_id = "jerry"
    was.temp.user_status = "active"
    was.temp.resouce = open ()
    
    return ...


Also there're another kind of method group,

.. code:: python

  @app.startup
  def startup (wasc, app):
    object = SomeClass ()
    wasc.registerObject ("myobject", object)
  
  @app.onreload  
  def onreload (wasc, app):
    wasc.myobject.reset ()
  
  @app.shutdown    
  def shutdown (wasc, app):
    wasc.myobject.close ()
  
'wasc' is class object of 'was' and mainly used for sharing Skitai server-wide object. these methods will be called,

1. startup: when app imported on skitai server started
2. onreload: when app.use_reloader is True and app is reloaded
3. shutdown: when skitai server is shutdowned
  

**Using WWW-Authenticate**

Saddle provide simple authenticate for administration or perform access control from other system's call.

.. code:: python

  app = Saddle (__name__)
  
  app.authorization = "digest"
  app.realm = "Partner App Area of mysite.com"
  app.user = "app"
  app.password = "iamyourpartnerapp"
	
  @app.route ("/hello/<name>")
  def hello (was, name = "Hans Roh"):
    return "Hello, %s" % name

If your server run with SSL, you can use app.authorization = "basic", otherwise recommend using "digest" for your password safety.



**Packaging for Larger App**

app.py

.. code:: python

  from skitai.saddle import Saddle
  from . import sub
  
  app = Saddle (__name__)
  app.debug = True
  app.use_reloader = True
  
  app.add_package (sub, "package")
  
  @app.route ("/")
  def index (was, num1, num2):  
    return was.ab ("hello", "Hans Roh") # url building


sub.py
  
.. code:: python

  from skitai.saddle import Package
  package = Package ()
  
  @package.route ("/hello/<name>")
  def hello (was):		
    # can build other module's method url
    return was.ab ("index", 1, 2) 
	  
You shoud mount only app.py. App's debug & use_reloader, etc. attributes will be applied to packages as same.


**Implementing XMLRPC Service**

Client Side:

.. code:: python

  import xmlrpc.client as rpc
  
  s = rpc.Server ("http://127.0.0.1:5000/rpc") # RPC App mount point
  result = s.add (10000, 5000)  
  
  
Server Side:

.. code:: python

  @app.route ("/add")
  def index (was, num1, num2):  
    return num1 + num2

Is there nothing to diffrence? Yes. Saddle app methods are also used for XMLRPC service if return values are XMLRPC dumpable.



Running Skitai as HTTPS Server
-------------------------------

Simply config your certification files to config file (ex. /etc/skitaid/servers-enabled/sample.conf). 

.. code:: python

    [server]
    ssl = yes
    ; added new key
    certfile = server.pem
    ; you can combine to certfile
    ; keyfile = private.key
    ; passphrase = 


To genrate self-signed certification file:

.. code:: python

    openssl req -new -newkey rsa:2048 -x509 -keyout server.pem -out server.pem -days 365 -nodes
    
For more detail please read REAME.txt in /etc/skitaid/cert/README.txt


Skitai with Nginx / Squid
--------------------------

From version 0.10.5, Skitai supports virtual hosting itself, but there're so many other reasons using with reverse proxy servers.

Here's some helpful sample works for virtual hosting using Nginx / Squid.

If you want 2 different and totaly unrelated websites:

- www.jeans.com
- www.carsales.com

And make two config in /etc/skitaid/servers-enabled

- jeans.conf *using port 5000*
- carsales.conf *using port 5001*

Then you can reverse proxying using Nginx, Squid or many others.

Example Squid config file (squid.conf) is like this:

.. code:: python
    
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


Project Purpose
-----------------

Skitai App Engine's original purpose is to serve python fulltext search engine Wissen_ which is my another pypi work. And recently I found that it is possibly useful for building and serving websites.

Anyway, I am modifying my codes to optimizing for enabling service on Linux machine with relatvely poor H/W and making easy to auto-scaling provided cloud computing service like AWS_.

If you need lots of outside http(s) resources connecting jobs and use PostgreSQL, it might be worth testing and participating this project.

Also note it might be more efficient that circumstance using `Gevent WSGI Server`_ + Flask. They have well documentation and already tested by lots of users.


.. _Wissen: https://pypi.python.org/pypi/wissen
.. _AWS: https://aws.amazon.com
.. _`Gevent WSGI Server`: http://www.gevent.org/
    

Installation and Startup
---------------------------

**Posix**

.. code:: python

    sudo pip install skitai    
    sudo skitaid.py -v &
    sudo skitaid.py stop

    ;if everythig is OK,
    
    sudo service skitaid start
    
    #For auto run on boot,
    sudo update-rc.d skitaid defaults
    or
    sudo chkconfig skitaid on
    

**Win32**

.. code:: python

    sudo pip install skitai
    cd c:\skitaid\bin
    skitaid.py -v
    skitaid.py stop (in another command prompt)
    
    ;if everythig is OK,
    
    install-win32-service install
    
    #For auto run on boot,
    install-win32-service --startup auto install
    
    install-win32-service start
    


Requirements
--------------

**Win 32**

- *pywin32 binary* - http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/

Optional Requirements
------------------------

* Skitaid can find at least one DNS server from system configuration for Async-DNS query. Possibly it is only problem on dynamic IP allocated desktop, then set DNS manually, please.

- *psycopg2* for querying PostgreSQL asynchronously (`win32 binary`_)
- *Jinja2* for HTML Rendering

.. _`win32 binary`: http://www.stickpeople.com/projects/python/win-psycopg/


Change Log
-------------
  
  0.11.4 - fix SSL proxy tunneling
  
  0.11.2 - add 'was' web socket service, was.ws, was.ws.lb, was.ws.map
  
  0.11.0 - Websocket implemeted
  
  0.10.7 - fix fail-reconnect issues related `was` networking services. fix proxy.
  
  0.10.6 - a) change sample config file name and sample site name from default.conf to sample.conf. 2) new config keys: response_timeout = 10, keep_alive = 10, see servers-enabled/sample.conf

  0.10.5 - add virtual hosting
  
  0.10.4 - bug fix py27's unicode type check
  
  0.10.3 - bug fix map-reduce call service. version number format was changed.
  
  0.10.1.8 - fix adns init point. DNS query will be more faster, if you unused proxy.
  
  0.10.1.3 - add was.temp.bind for event handling
  
  0.10.1.1 - add was.temp for setting temporary data during current request
  
  0.10.1.0 - enter 0.10 beta state
  
  0.10.0.5 - keep-alive & data transfer dealy timeout was reset
  
  0.10.0.4 - add execution time & delivery time to request log file
  
  0.10.0.2 - emergency patch for str responses, add Digest auth method for was remote call

  0.10.0 - WSGI support
    
  0.9.4.21 - add tools
  
  0.9.4.19 - no threads mode, then can config threads=0, but cannot use all async restful requests
  
  0.9.4.17 - fix application reload in py27
 
  0.9.4.16 - fix GZIP decompressing
  
  0.9.4.13 - enable pass phrase on CA signed certification
  
  0.9.4.9 - remove dependency M2Crypto
  
  0.9.4.8 - fix error handling for asynconnect.connect
  
  0.9.4.6 - improve handling winsock ENOTCONN
  
  0.9.4.5 - fix asyndns, asyncon reconnect
  
  0.9.4.1 - fix init.d script

  0.9.4 - (1)works on Python 3, but unstable yet (2)add was.email() (3)improve rpc performance
  
  0.9.3.7 - add skitaid-install-requirements.sh for psycopg2 and M2Crypto
	  
  0.9.3.2 - change default log and var path 
 
  0.9.2 - fix multipart file upload
  
  0.9.1.32 - fix reverse proxy Host header

  0.9.1.30 - was.wget, was.rest (former was.rpc), was.map, was.lb specification changed. see Documentation.
  
  0.9.1.28 - add HEAD, DELETE, OPTIONS methods
  
  0.9.1.27 - support Map-Reduce, Load_Balanace for (json & xml serialized object over) HTTP Call
  
  0.9.1.25 - fix xmlrpc server uri, I misunderstood all xmlrpc uri is /rpc2
  
  0.9.1.24 - possibly fixed, "too many file descriptors in select()"
  
  0.9.1.23 - add some methods to was.request, add "X-Forwarded-For" to proxy_handler
  
  0.9.1.19 - new was member, was.response
      
  0.9.1.14 - Automation session commit
  
  0.9.1.12 - Fix / App Routing