Skitai App Engien Library
==========================

Copyright (c) 2015 by Hans Roh

License: BSD

Introduce
----------

Skitai App Engine Library (SAEL) is a kind of branch of `Medusa Web Server`__ - A High-Performance Internet Server Architecture.

Medusa is different from most other servers because it runs as a single process, multiplexing I/O with its various client and server connections within a single process/thread.

SAEL orients light-weight and strengthen networking jobs with external resources - HTTP / HTTPS / RPC / PostgreSQL_ - keeping very low costs.

 - It can run as XML/JSON-RPC & Web Server.
 - It can request massive RPC/HTTP(S) connections supported by asynchronous socket framework at your apps easily.
 - Provide asynchronous PostgreSQL query execution

It also influenced by Zope_ and Flask_ a lot.


.. _Zope: http://www.zope.org/
.. _Flask: http://flask.pocoo.org/
.. _PostgreSQL: http://www.postgresql.org/
.. __: http://www.nightmare.com/medusa/medusa.html


Requirements
-------------
*Psycopg2* for PostgreSQL

(Optioanl)

- *M2Crypto* for HTTPS Web Server
- *jsonrpclib* for serving JSON-RPC
- *Jinja2* for HTML Rendering


Documentation
-------------

	Please visit https://gitlab.com/hansroh/skitai/wikis/home



