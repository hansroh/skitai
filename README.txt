Skitai App Engien Library
==========================

Copyright (c) 2015 by Hans Roh

License: BSD


Introduce
----------

Skitai App Engine Library (SAEL) is a kind of branch of `Medusa Web Server`__ - A High-Performance Internet Server Architecture.

Medusa is different from most other servers because it runs as a single process, multiplexing I/O with its various client and server connections within a single process/thread.

SAEL orients light-weight,simplicity  and strengthen networking operations with external resources - HTTP / HTTPS / RPC / PostgreSQL_ - keeping very low costs.

It also influenced by Zope_ and Flask_ a lot.

- It can be run as XML/JSON-RPC, Web and Proxy & Loadbancing Server.
- It can request massive RPC/HTTP(S) connections based on asynchronous socket framework at your apps easily.
- It provides asynchronous PostgreSQL query execution

Skitai is not a framework for combinient developing, module reusability and plugin flexibility etc. It just provides some powerful communicating services for your apps as both server and client.


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
    [@mysearch]
    members = s1.yourserver.com:5000,s2.yourserver.com:5000,s3.yourserver.com:5000



.. code:: python

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


**RPC Load-Balancing**

.. code:: python

    @app.route ("/search")
    def search (was, keyword = "Mozart"):
      s = was.lb ("mysearch/rpc2")
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
      s = was.dmap ("mydb")
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


Requirements
-------------

* *Currently only tested in Python 2.7*

* Skitaid can find at least one DNS server from system configuration for Async-DNS query. Possibly it is only problem on dynamic IP allocated desktop, then set DNS manually, please.


**Posix**

- *psycopg2* for PostgreSQL

*(Optional)*

- *M2Crypto* for HTTPS Web Server
- *jsonrpclib* for serving JSON-RPC
- *Jinja2* for HTML Rendering

Use 'pip install ...'


**Win 32**

- *pywin32 binary* - http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/
- *psycopg2 binary* - http://www.stickpeople.com/projects/python/win-psycopg/

*(Optional)*

- *M2Crypto binary* - https://github.com/saltstack/salt-windows-install/tree/master/deps/win32-py2.7
- *jsonrpclib* for serving JSON-RPC
- *Jinja2* for HTML Rendering


Documentation
-------------

    Please visit https://gitlab.com/hansroh/skitai/wikis/home


Change Log
-------------
<<<<<<< HEAD
  0.9.1.23 - add some methods to was.request, add "X-Forwarded-For" to proxy_handler
  
=======
>>>>>>> c1681884e6de5fb048145a582b87b0f68a3a0ede
  0.9.1.20 - fix bug for static file response
  
  0.9.1.19 - new was member, was.response
  
  0.9.1.18 - ignore EWOULDBLOCK raised with multi-workers on posix
  
  0.9.1.17 - Fix adns double callbacking on posix machine, external networking works fine
  
  0.9.1.16 - Add streaming response
  
  0.9.1.15 - Improve consistency of handlers' exception handling
      
  0.9.1.14 - Automation session commit
    
  0.9.1.13 - Fix ip= config and add README.md (incompleted)
  
  0.9.1.12 - Fix / App Routing
    
  0.9.1.11 - Change sample configuration files and bug fix skitaid.py
  
  0.9.1.10 - Found lots of requirements I didn't think