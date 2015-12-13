
Skitai WSGI App Engine
==========================

Copyright (c) 2015 by Hans Roh

License: BSD

Announcement
---------------

From version 0.10, Skitai App Engine follows WSGI specification. So previous Skitai apps need to a few modifications.

Conceptually, SAE has been seperated to two components: 

1. Skitai App Engine Server, for WSGI apps

2. Saddle, the small WSGI middleware integrated with SAE. But you can also mount any WSGI apps and frameworks like Flask.


Introduce
----------

Skitai App Engine (SAE) is a kind of branch of `Medusa Web Server`__ - A High-Performance Internet Server Architecture.

Medusa is different from most other servers because it runs as a single process, multiplexing I/O with its various client and server connections within a single process/thread.

SAE orients light-weight, simplicity  and strengthen networking operations with external resources - HTTP / HTTPS / XML-RPC / PostgreSQL_ - keeping very low costs.

It is influenced by Zope_ and Flask_ a lot.

- SAE can be run as XML/JSON-RPC, Web and Reverse Proxy Loadbancing Server
- SAE can handle massive RESTful API/RPC/HTTP(S) connections based on asynchronous socket framework at your apps easily
- SAE provides asynchronous connection to PostgreSQL

Skitai is not a framework for convinient developing, module reusability and plugin flexibility etc. It just provides some powerful communicating services for your WSGI apps as both server and client.


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

For mounting to SAE, modify config file in /etc/skitaid/servers-enabled/default.conf

.. code:: python
  
  [routes:line]
  
  ; for files like images, css
  / = /var/wsgi/static
  
  ; app mount syntax is path/module:callable
  / = /var/wsgi/wsgiapp:app
  /aboutus = /var/wsgi/flaskapp:app
  /services = /var/wsgi/skitaiapp:app
  
That's it.

You can access Falsk app from http://www.domain.com/aboutus and other apps are same.



Using Asynchronous Requests Provide by SAE
----------------------------------------------------------

**Simple HTTP GET Request**

*Flask Style:*

.. code:: python

  from flask import Flask
  from skitai import was
  
  app = Flask (__name__)        
  @app.route ("/get")
  def get (url):
    s = was.wget (url)
    result = s.getwait (5) # timeout
    return result.data


*Skitai-Saddle Style*

.. code:: python

  from skitai.saddle import Saddle
  app = Saddle (__name__)
        
  @app.route ("/get")
  def get (was, url):
    s = was.rest (url)
    result = s.getwait (5) # timeout
    return result.data


**XMLRPC Load-Balancing**

Add mysearch members to config file,

.. code:: python

    [@mysearch]
    ssl = yes
    members = search1.mayserver.com:443, search2.mayserver.com:443
    

Then SAE will request result from one of mysearch members.
   
.. code:: python

    @app.route ("/search")
    def search (was, keyword = "Mozart"):
      s = was.map ("@mysearch/rpc2", "XMLRPC")
      s.search (keyword)
      results = s.getwait (2)      
			return result.data


**For XMLRPC Map-Reducing**

Basically same with load_balancing except SAE requests to all members.

.. code:: python

    @app.route ("/search")
    def search (was, keyword = "Mozart"):
      s = was.map ("@mysearch/rpc2", "XMLRPC")
      s.search (keyword)
      results = s.getswait (2)
			
			all_results = []
      for result in results:
         all_results.extend (result.data)
      return all_results


**PostgreSQL Map-Reducing**

Also similiar with above.
Add mydb members to config file.

.. code:: python

    [@mydb]
    type = postresql
    members = s1.yourserver.com:5432/mydb/user/passwd,s2.yourserver.com:5432/mydb/user/passwd


.. code:: python

    @app.route ("/query")
    def query (was, keyword):
      s = was.dmap ("@mydb")
      s.execute("SELECT * FROM CITIES;")

      results = s.getswait (timeout = 2)

      all_results = []
      for result in results:
        if result.status == 3:
          all_results.append (result.data)
      return all_results
      


Project Purpose
-----------------

Skitai App Engine's original purpose is to serve python fulltext search engine Wissen_ which is my another pypi work. And recently I found that it is possibly useful for building and serving websites.

Anyway, I am modifying my codes to optimizing for enabling service on Linux machine with relatvely poor H/W and making easy to auto-scaling provided cloud computing service like AWS_.

If you need lots of outside http(s) resources connecting jobs and use PostgreSQL, it might be worth testing and participating this project.


.. _Wissen: https://pypi.python.org/pypi/wissen
.. _AWS: https://aws.amazon.com

    

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


    
Documentation
-------------
  
  I'm so sorry, there's only very old documentation.
  
  https://gitlab.com/hansroh/skitai/wikis/home
  
  Fundemental concept and structure is not so changed, so it's better than none.


Change Log
-------------
  
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
