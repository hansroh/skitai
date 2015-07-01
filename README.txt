Skitai App Engien Library
==========================

Copyright (c) 2015 by Hans Roh

License: BSD



Apology
----------

I'm very sorry for lots of unstable releases. I never expect over a thousand downloads even within a day.

Please forgive me, this is my first participating to PIP, then so confused and scared...

I think version 0.9.1.11 can be worked with relatively less efforts. Please update skitai and recopy implements/skitaid.

I hope basic documentation is written within this weekend.


Introduce
----------

Skitai App Engine Library (SAEL) is a kind of branch of `Medusa Web Server`__ - A High-Performance Internet Server Architecture.

Medusa is different from most other servers because it runs as a single process, multiplexing I/O with its various client and server connections within a single process/thread.

SAEL orients light-weight and strengthen networking operations with external resources - HTTP / HTTPS / RPC / PostgreSQL_ - keeping very low costs.

- It can run as XML/JSON-RPC & Web Server.
- It can request massive RPC/HTTP(S) connections based on asynchronous socket framework at your apps easily.
- Provide asynchronous PostgreSQL query execution

It also influenced by Zope_ and Flask_ a lot.


.. _Zope: http://www.zope.org/
.. _Flask: http://flask.pocoo.org/
.. _PostgreSQL: http://www.postgresql.org/
.. __: http://www.nightmare.com/medusa/medusa.html


Requirements
-------------

*Currently only tested in Python 2.7*


**Win 32**

- *pywin32 binary* - http://sourceforge.net/projects/pywin32/files/pywin32/Build%20219/
- *psycopg2 binary* - http://www.stickpeople.com/projects/python/win-psycopg/

*(Optional)*

- *M2Crypto binary* - https://github.com/saltstack/salt-windows-install/tree/master/deps/win32-py2.7
- *jsonrpclib* for serving JSON-RPC
- *Jinja2* for HTML Rendering

**Posix**

- *psycopg2* for PostgreSQL

*(Optional)*

- *M2Crypto* for HTTPS Web Server
- *jsonrpclib* for serving JSON-RPC
- *Jinja2* for HTML Rendering

Use 'pip install ...'


Documentation
-------------

	Please visit https://gitlab.com/hansroh/skitai/wikis/home


Change Log
-------------
	
	0.9.1.13 - Add README.md
  
  0.9.1.12 - Fix / App Routing
	
  0.9.1.11 - Change sample configuration files and bug fix skitaid.py
  
  0.9.1.10 - Found lots of requirements I didn't think