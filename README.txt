Skitai App Engien
==========================

Copyright (c) 2015 by Hans Roh

License: BSD


Introduce
----------

Skitai App Engine (SAE) is a kind of branch of `Medusa Web Server`__ - A High-Performance Internet Server Architecture.

Medusa is different from most other servers because it runs as a single process, multiplexing I/O with its various client and server connections within a single process/thread.

SAE orients light-weight,simplicity  and strengthen networking operations with external resources - HTTP / HTTPS / RPC / PostgreSQL_ - keeping very low costs.

It also influenced by Zope_ and Flask_ a lot.

- It can be run as XML/JSON-RPC, Web and Proxy & Loadbancing Server.
- It can request massive RESTful api/RPC/HTTP(S) connections based on asynchronous socket framework at your apps easily.
- It provides asynchronous PostgreSQL query execution

Skitai is not a framework for convinient developing, module reusability and plugin flexibility etc. It just provides some powerful communicating services for your apps as both server and client.


Purpose
--------

Skitai App Engine's earlier purpose is to serve python fulltext search engine Wissen_ which is my another pypi work. And recently I found that it is possibly useful for building and serving python written websites like Flask and Django (But I barely use them). I think you already use them, you really don't need use Skitai.

Anyway, I am modifying my codes to optimizing for enabling service on Linux machine with relatvely poor H/W and making easy to auto-scaling provided cloud computing service like AWS_.

If you need lots of outside http(s) resources connecting jobs and use PostgreSQL, it might be worth testing and participating this project.


Changes
---------

**Config changed**

M2Crypto dependency has been removed, then [certification] section had been entirely removed.

.. code:: python

    [server]
    ssl = yes
    ; added new key
    certfile = server.pem


To genrate self-signed certification file:

.. code:: python

    openssl req -new -newkey rsa:2048 -x509 -keyout server.pem -out server.pem -days 365 -nodes
    

**New services added**

.. code:: python

    # streaming response for stream objects like file, large string list...
    # object should have read() and optioanl close() method
    return was.tostream (open ("large-movie.mp4", "rb"))
    
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



At a Glance
------------

**Basic Configure**

.. code:: python

    [server]
    processes = 1
    threads = 4
    port = 5000

    [routes:line]
    / = /home/skitaid/app/static
    / = /home/skitaid/app/webapp


**Hello World**

Then write /home/skitaid/app/webapp.py

.. code:: python

    from skitai.server import ssgi
    
    app = ssgi.Application (__name__)
    app.set_devel (True)
        
    @app.route ("/hello")
    def hello (was):
        return 'Hello World'

**For RPC Map-Reducing**

.. code:: python

    ; add mysearch members to config file
    [@mypypi]
    ssl = yes
    members = pypi1.python.org:443, pypi2.python.org:443

.. code:: python

    @app.route ("/search")
    def search (was, keyword = "Mozart"):
      s = was.map ("@mypypi/pypi")
      s.search (keyword)

      results = s.getswait (timeout = 2)

      all_results = []
      for result in results:
        if result.status == 3:
          all_results.extend (result.data)
      return all_results


**RPC Load-Balancing**

.. code:: python

    @app.route ("/search")
    def search (was, keyword = "Mozart"):
      s = was.lb ("@mypypi/pypi")
      s.search (keyword)

      return s.getwait (timeout = 2)


**For PostgreSQL Map-Reducing**

.. code:: python

    ; add mydb members to config file
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


.. _Zope: http://www.zope.org/
.. _Flask: http://flask.pocoo.org/
.. _PostgreSQL: http://www.postgresql.org/
.. __: http://www.nightmare.com/medusa/medusa.html
.. _Wissen: https://pypi.python.org/pypi/wissen
.. _AWS: https://aws.amazon.com


Requirements
--------------

**Win 32**

- *pywin32 binary* - http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/



Optional Requirements
------------------------

* Skitaid can find at least one DNS server from system configuration for Async-DNS query. Possibly it is only problem on dynamic IP allocated desktop, then set DNS manually, please.


**Posix**

- *psycopg2* for querying PostgreSQL asynchronously
- *Jinja2* for HTML Rendering

Use 'pip install ...'


**Win 32**

- *psycopg2 binary* - http://www.stickpeople.com/projects/python/win-psycopg/
- *Jinja2* for HTML Rendering


Install & Start Skitai Server
------------------------------

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
    

Documentation
-------------

    Please visit https://gitlab.com/hansroh/skitai/wikis/home


Change Log
-------------
  
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
