# Skitai App Engine

Skitai is a Python WSGI/HTTP Server for UNIX.

And simple to run:

Install,

```bash
    pip3 install -U skitai
```

Create and mount your app,
```python
# serve.py
def app (env, start_response):
    start_response ("200 OK", [("Content-Type", "text/plain")])
    return 'Hello World'

if __name__ == "__main__":
    import skitai

    skitai.mount ('/', app)
    skitai.mount ('/', '/var/www/statics')
    skitai.run (address = "127.0.0.1", port = 5000)
```

And run.

```python
    python3 serve.py
```

Your app will work for your thousands or miliions of customers.

**Features**

- Mount multiple apps: Flask and Django can be mounted at the same time
- Websocket
- HTTP 2.0 h2c protocol based on [h2](https://github.com/python-hyper/h2)







# Installation
## Requirements

Python 3.6+

## Installation

Skitai and other core base dependent libraries is developing on
single milestone, install/upgrade all at once. Otherwise it is
highly possible to meet some errors.

With pip

```bash
pip3 install -U skitai rs4 aquests
```

With git
```bash
pip3 install -U rs4 aquests
git clone https://gitlab.com/hansroh/skitai.git
cd skitai
pip3 install -e .
```


# Usage

## Mount Resources
### Mount WSGI Apps
```python
import skitai

if __name__ == "__main__":
    # mount Flask something
    skitai.mount ('/', 'my_flask/myapp:app')
    # mount Django
    skitai.mount ('/admin', 'my_django/my_django/wsgi:application')
    skitai.run (ip = '0.0.0.0', port = 5000)
```

### Mount Directories
```python
    skitai.mount ('/', 'my_proejct/root')
    skitai.mount ('/static', 'my_proejct/static')
    skitai.mount ('/media', 'my_proejct/media')
```

### Mount HTTP Services
```python
    # HTTP
    # load-balancing if multiple  members
    skitai.alias ('@external', skitai.PROTO_HTTPS, ["www1.server.com", "www2.server.com"])
    skitai.mount ('/external', '@external/api')
```
- PROTO_HTTP
- PROTO_HTTPS

### Runtime App Preference
```python
with skitai.preference () as pref:
    pref.debug = True
    pref.use_reloader = True
    skitai.mount ('/', app, pref)
skitai.run ()
```
All attributes of pref will overwrite your app attrubutes.






## Launching Service
### Run in Console
```bash
python3 serve.py
```

### Run as Daemon
```
python3 serve.py start # start service
python3 serve.py stop
python3 serve.py restart
```

### Run with Systemd
Give a name like `myservice`
```python
skitai.run (ip = '0.0.0.0', port = 5000, name = 'myservice')
```

```bash
# create systemd config in /etc/systemd/system/myservice.service
python3 serve.py install
# update /etc/systemd/system/myservice.service
python3 serve.py update
```

```bash
# start as root, but fallback into current sudoer after started up
sudo python3 serve.py install

# start as root, but change into user skitai, group www
sudo python3 serve.py --user skitai --group www install

# to keep root privilege
sudo python3 serve.py --user root install

sudo python3 serve.py uninstall
```

To startup or stop,
```bash
sudo systemctl start myservice
sudo systemctl stop myservice
sudo systemctl restart myservice
```

### Command Line Parameters
```bash
python3 serve.py --help
```

skitai.run parameters,

```python
skitai.run (ip = '0.0.0.0', port = 5000, thread = 1, workers = 4)
```

But command line options have more high pripority.
```bash
python3 serve.py --threads=4 --workers=2 --port 38000
```

To adding custom options,
```python
skitai.add_option ("-q", '--qtran', 'start queued transaction service')
skitai.add_option (None, '--temp-dir=TEMP_DIR', 'temp directory', default = '/var/tmp/myservice')

if "--qtran" in skitai.options:
    tasks.add ('transaction')
os.mkdir (skitai.options ['--temp-dir'])
```

```bash
python3 serve.py --help
Usage: ./serve.py [OPTION]... [COMMAND]
COMMAND can be one of [start|stop|status|restart|install|uninstall|remove|update]

Mandatory arguments to long options are mandatory for short options too.
...
-q,  --qtran                 start queued transaction daemo
     --temp-dir=TEMP_DIR     temp directory
```

To update systemd service,
```bash
sudo python3 serve.py --user skitai --qtran --temp-dir=/path/to update
sudo systemctl restart myservice
```





## HTTP/2.0 Push

It will works only if HTTP/2.0 h2c requests. Otherwise ignored.

```python3
from flask import render_template

@app.route ('/promise')
def promise ():
    skitai.push ('/img/logo.png')
    skitai.push ('/img/main.png')
    # index.j2 contains above images
    return render_template ('index.j2')
```






## Websocket

Flask app example,

```python
# flask app example
from flask import request

@app.route ("/echo3")
@skitai.websocket (timeout = 60)
def echo ():
    ws = request.environ ["websocket"]
    ws.send ("hello")
    while 1:
        message = yield
        if not message:
            return #strop iterating
        yield "ECHO:" + message
```

Some browsers do not support WWW-Authenticate on websocket
like Safari, then Skitai currently disables WWW-Authenticate
for websocket, so you should be careful for requiring secured
messages.





## Inter Workers Shared States
```python
skitai.register_g ('DB_STATUS')
skitai.register_g ('TOTAL_CLIENTS')
skitai.mount ('/', app)
skitai.run ()
```

Your app can use like dictionary.
```python
skitai.g ['DB_STATUS'] = 4
```

This object will be shared by all workers.







## Logging
### Filter Request Logging
```python
# turned off starting with
skitai.log_off ('/static/')
# turned off ending with
skitai.log_off ('*.css')
# you can multiple args
skitai.log_off ('*.css', '/static/images/', '/static/js/')
```

### Enable File Logging
```python
skitai.enalbe_file_logging ()
```

Log files will be created at /var/log/skitai/{SERVICE_NAME},
- request.log
- server.log

### Log Format

Blank seperated items of log line are,

- log date
- log time
- client ip or proxy ip

- request host: default '-' if not available
- request methods
- request uri
- request version
- request body size

- reply code
- reply body size

- global transaction ID: for backtracing request if multiple backends related
- local transaction ID: for backtracing request if multiple backends related
- username when HTTP auth: default '-', wrapped by double quotations
  if value available
- bearer token when HTTP bearer auth

- referer: default '-', wrapped by double quotations if value available
- user agent: default '-', wrapped by double quotations if value available
- x-forwared-for, real client ip before through proxy

- Skitai engine's worker ID like W0, W1 (Worker #0, #1,...)
- number of active connections
  include not only clients but your backend/upstream servers
- duration ms for request handling
- duration ms for transfering response data






# Test Client

To test full mounted resources with many protocols.

```python
import skitai
import route_guide_pb2

def test_myservice ():
    with skitai.test_client ("./serve.py", 6000) as cli:
        resp = cli.get ("/")
        assert resp.status_code == 200
        assert "something" in resp.text

        resp = cli.get ("/static/app.js")
        assert resp.status_code == 200

        # test JSON API
        resp = cli.axios.get ('/pets/45')
        assert resp.status_code == 200
        assert resp.josn ()['id']== 45

        # test thru HTTP/2
        resp = cli.http2.get ("/")
        assert resp.status_code == 200
        assert "something" in resp.text

        with cli.stub ('/api') as stub:
            resp = stub.get ('/profiles')
            assert resp.status_code == 200


        # test RPCs
        with cli.jsonrpc ("/rpc2") as stub:
            assert stub.add (4, 10) == 14

         with cli.xmlrpc ("/rpc2") as stub:
            assert stub.add (4, 10) == 14

        with cli.grpc () as stub:
            summary = stub.RecordRoute (point_iter ())
            assert isinstance (summary, route_guide_pb2.RouteSummary)
```

For end-to-end test using Chrome driver,

```bash
sudo apt update
sudo apt -y install chromium-chromedriver
sudo pip3 install -Ur selenium lxml==4.4.0 cssselect==0.9.1 html5lib==0.999999999
```

```python
import skitai

def test_myservice ():
    with skitai.test_client ("./serve.py", 6000) as cli:
        # E2E test
        with cli.driver as driver:
            driver.navigate ('/apis/auth/login?return_url=%2Farticles%3Fcategory%3D3')
            email_input = driver.one ("input[type=text]", 'visible')
            assert email_input, "cnnot find username input"
            email_input.send_keys ("{}\t{}\n".format (user, pw))
            driver.one ('img[src="/assets/image/icon_home.png"]', 'visible')
            e = driver.one ('header')
            assert 'My Page' in e.text
            driver.capture ()
```

To test already running server on port 6000, remove script path,

```python
with skitai.test_client (port = 6000) as cli:
    resp = cli.get ("/")
```






# Change Log

- 0.36 (Apr, 2021)

  - add Preference.set_static () and Preference.set_media ()
  - change default export script from __export__.py to wsgi.py
  - rewrite this documentation
  - rename coreauest to Task

- 0.35 (Feb 2020)

  - drop support win32 platform officially
  - add coroutine with corequest
  - add was.cursor ()
  - add skitai.set_503_estimated_timeout (timeout)
  - multiple Atila apps and ONE Not-Atila app can be mounted to same path
  - add was.stub ()
  - drop supporing Python 3.5 officially
  - add was.flashfile with auto deletion file name
  - disable pebble_ executor by process cleanup problem
  - drop officicial support for pypy3, few perf. improvement
    but some compatable errors
  - use pebble_ for timeout managed process pool
  - remove ujson-ia dependency, it may have memory leak
  - reengineering threading locks for asynconnect, http_channels
    and http2/3 handlers
  - from version 0.35.2, required aioquic>=0.9 if you need HTTP/3
  - add dict () method to was.Tasks
  - add 'filter' argument to was.Thread, Process and Subprocess
  - change dependency: ujosn => ujson-ia
  - add app.config.PRETTY_JSON (default is False, 2 spaces indented JSON format)
  - drop support Python 3.5 officially
  - catch SIGHUP for reloading worker process
  - add skitai command: install, remove and update for systemctl script
  - add sktai.get_option (\*options)
  - make aioquic installation optional
  - update Django reloader for 2.xx
  - fix corequest cache expiring
  - support h3-25, h3-26
  - add skitai.set_max_was_clones_per_thread (val)
  - fix corequest cache
  - deprecate corequest.Task(s) keyword arguments, instead add meta
    argument
  - enable Range header to WSGI content

- 0.34 (Jan 2020)

  - fix proxy and proxypass for PATCH method
  - add `--devel` and `--silent` runtime options
  - remove `--production` runtime options
  - lower version comaptible: change app bootstraping
    function name: bootstrap -> \_\_setup\_\_

- 0.32 (Oct 2019)

  - initiate HTTP3+QUIC, you can test HTTP/3 with Chrome Canary

- 0.31 (Sep 2019)

  - change handling command line options, required rs4>=0.2.5.0
  - add skitai.set_smtp ()
  - remove protobuf, redis, pymongo and psycopg2 from requirements,
    if you need these, install them maually
  - skitai.preference () can be used with context
  - fix http/2 response delaying when body is not exist
  - skitai.enable_forward () can forward to single domain
  - add dropping root privileges when Skitai run with sudo for using
    under 1024 ports etc.
  - refix: master process does not drop root privileges for clean resources
  - fix reloading for file mounted apps
  - confirmed to work on PyPy3

- 0.30 (Sep 2019)

  - skitai.websocket spec changed, lower version compatable

- 0.29 (Aug 2019)

  - add was.Subprocess
  - add handlers for Range, If-Range, If-Unmodified-Since, If-Match headers
  - asyncore and asynchat are vendored as rs4.asyncore and chat,
    because they will be exsanguinated from standard Python library.
    Mr. Rossum has been listed up on my mortal enemy list
  - deprecated: was.Future and was.Futures, it doesn't need. for
    using returning (), use corequest.returning () and was.Tasks.returning ()
  - new corequest.pth package
  - over 100 unit tests

- 0.28 (Feb 2019)

  - fix auto reloading bug in case multiple apps are mounted
  - add was.Thread () and was.Process ()
  - add @skitai.states () decorator
  - rename skitai.deflu () => skitai.register_states ()
  - add corequest object explaination and corequest based model example
  - drop SQLAlchemy query statement object
  - fix https proxypass, and add proxypass remapping
  - add was.transaction ()
  - update psycopg2 connection parameter: async => async\_
    for Py3.7 compatablity
  - replace from data_or_thow (), one_or_throw () to fetch (), one ()
  - fix HTTP2 server push and add was.push ()
  - getwait () and getswait () are integrated into dispatch ()
  - add data_or_throw () and one_or_throw ()
  - was.promise has been deprecated, use was.futures: see Atila documentation
  - reinstate gc.collect () schedule
  - fix GTXID
  - fix app reloader
  - remove gc.collect () schedule
  - support SQLAlchemy query statement object
  - removed sugar methods: was.getjson, getxml, postjson, ...,
    instead use headers parameter or app.config.default_request_type
  - skitai.win32service has been moved to rs4.psutil.win32service
  - improve 'was' magic method search speed
  - seperate skitai.saddle into atila

- 0.27.6 (Jan 2019)

  - rename directory decorative to services
  - change from skital.saddle.contrib.decorative to
    skital.saddle.contrib.services

- 0.27.3 (May 2018)

  - remove -v option from skitai and smtpda
  - add script: skitai
  - remove scripts: skitai-smtpda and skitai-cron
  - remove skitai.enable_smtpda (), skitai.cron ()

- 0.27.2 (May 2018)

  - add was.request.get_real_ip () and was.request.is_private_ip ()
  - fix CORS preflight

- 0.27.1 (May 2018)

  - sqlphile bug fixed and change requirements

- 0.27 (Apr 2018)

  - add app.setup_sqlphile ()
  - add @app.mounted_or_reloaded decorator
  - removed @app.auth_required, added @app.authorization_required (auth_type)
  - rename @app.preworks -> @app.run_before and @app.postworks
    ->  @app.run_after
  - add @app.bearer_handler
  - add was.mkjwt and was.dejwt
  - add was.timestamp amd was.uniqid
  - renamed was.token -> was.mktoken
  - renamed api -> API, for_api -> Fault
  - skitai.use_django_models has been deprecated, use skitai.alias
  - functions are integrated skitai.mount_django into skitai.mount,
    skitai.alias_django into skitai.alias
  - fix empty payload posting
  - add was.partial and was.basepath
  - raise NameError when non-exists funtion name to was.ap
  - fix default arg is missing on was.ab
  - add skitai.launch and saddle.make_client for unittest

0.26 (May 2017)

- 0.26.18 (Jan 2018)

  - fix HTTP2 trailers
  - fix HTTP2 flow control window
  - remove was.response.traceback(), use was.response.for_ap (traceback = True)
  - rename was.sqlmap to was.sql
  - add @app.auth_required and  @app.auth_not_required decorator
  - change default export script to __export__.py
  - remove app reloading progress:

    - before:

      - before_umount (was)
      - umounted (wac)
      - before_remount (wac): deprecated
      - remounted (was): deprecated

    - now:

      - before_reload (was)
      - reloaded (was)

  - change app.model_signal () to app.redirect_signal (), add @app.on_signal ()
  - change skitai.addlu to skitai.deflu (args, ...)
  - add @app.if_file_modified
  - add @app.preworks and @app.postworks
  - fix HTTP/2 remote flow control window
  - fix app.before_mount decorator exxcute point
  - add was.gentemp () for generating temp file name
  - add was.response.throw (), was.response.for_api()
    and was.response.traceback()
  - add @app.websocket_config (spec, timeout, onopen_func,
    onclose_func, encoding)
  - was.request.get_remote_addr considers X-Forwarded-For header
    value if exists
  - add param keep param to was.csrf_verify()
  - add and changed app life cycle decorators:

    - before_mount (wac)
    - mounted (was)
    - before_remount (wac)
    - remounted (was)
    - before_umount (was)
    - umounted (wac)

  - add skitai.saddle.contrib.django,auth for integrating Django authorization
  - change was.token(),was.detoken(), was.rmtoken()
  - add jsonrpc executor
  - add some methods to was.djnago: login (), logout (), authenticate ()
    and update_session_auth_hash ()
  - add app.testpass_required decorator
  - add decorative concept

- 0.26.17 (Dec 2017)

  - can run SMTP Delivery Agent and Task Scheduler with config file
  - add error_handler (prev errorhandler) decorator
  - add default_error_handler (prev defaulterrorhandler) decorator
  - add login_handler, login_required decorator
  - add permission_handler, permission_required decorator
  - add app events emitting
  - add was.csrf_token_input, was.csrf_token and was.csrf_verify()
  - make session iterable
  - prevent changing function spec by decorator
  - change params of use_django_models: (settings_path, alias),
    skitai.mount_django (point, wsgi_path, pref = pref (True),
    dbalias = None, host = "default")

- 0.26.16 (Oct 2017)

  - add app.sqlmaps
  - add use_django_models (settings_path), skitai.mount_django
    (point, wsgi_path, pref = pref (True), host = "default")
  - fix mbox, add app.max_client_body_size
  - add skitai.addlu (args, ...)
  - fix promise and proxing was objects
  - change method name from skitai.set_network_timeout to set_erquest_timeout
  - fix getwait, getswait. get timeout mis-working
  - fix backend_keep_alive default value from 10 to 1200
  - fix dbi reraise on error
  - JSON as arguments

- 0.26.15

  - added request.form () and request.dict ()
  - support Django auto reload by restarting workers
  - change DNS query default protocol from TCP to UDP (posix only)
  - add skitai.set_proxy_keep_alive (channel = 60, tunnel = 600)
    and change default proxy keep alive to same values
  - increase https tunnel keep alive timeout to 600 sec.
  - fix broad event bus
  - add getjson, deletejson, this request automatically add header
    'Accept: application/json'
  - change default request content-type from json to form data,
    if you post/put json data, you should change postjson/putjson
  - add skitai.trackers (args,...) that is equivalant to skitai.lukeys ([args])
  - fix mounting module
  - app.storage had been remove officially, I cannot find any usage. but unoficially
    it will be remains by some day
  - add skitai.lukeys () and fix inconsistency of was.setlu
    & was.getlu between multi workers
  - was.storage had been remove
  - add skitai.set_worker_critical_point ()
  - fix result object caching
  - add app.model_signal (), was.setlu () and was.getlu ()

- 0.26.14

  - add app.storage and was.storage
  - removed wac._backend and wac._upstream, use @app.mounted and @app.umount
  - replaced app.listen by app.on_broadcast

- 0.26.13

  - add skitai.log_off (path,...)
  - add reply content-type to request log, and change log format
  - change posix process display name

- 0.26.12

  - change event decorator: @app.listen -> @app.on_broadcast
  - adaptation to h2 3.0.1
  - fix http2 flow controling
  - fix errorhandler and add defaulterrorhandler
  - fix WSGI response handler
  - fix cross app URL building
  - Django can be mounted
  - fix smtpda & default var directory
  - optimize HTTP/2 response data
  - fix HTTP/2 logging when empty response body
  - http_response.outgoing is replaced by deque
  - change default mime-type from text/plain to
    application/octet-stream in response header
  - HTTP response optimized

- 0.26.10

  - start making pytest scripts
  - add was-wide broadcast event bus: @app.listen (event),
    was.broadcast (event, args...) and @was.broadcast_after (event)
  - add app-wide event bus: @app.on (event), was.emit (event, args...)
    and @was.emit_after (event)
  - remove @app.listento (event) and was.emit (event, args...)

- 0.26.9

  - add event bus: @app.listento (event) and was.emit (event, args...)

- 0.26.8

  - fix websocket GROUPCHAT
  - add was.apps
  - was.ab works between apps are mounted seperatly

- 0.26.7

  - add custom error template on Saddle
  - add win32 service tools
  - change class method name from make_request () to backend ()
  - retry once if database is disconnected by keep-live timeout
  - drop wac.make_dbo () and wac.make_stub ()

- 0.26.6

  - add wac.make_dbo (), wac.make_stub () and wac.make_request ()
  - wac.ajob () has been removed
  - change repr name from wasc to wac
  - websocket design spec, WEBSOCKET_DEDICATE_THREADSAFE has been
    removed and WEBSOCKET_THREADSAFE is added
  - fix websocket, http2, https proxy tunnel timeout, related
    set_network_timeout () is recently added

- 0.26.4.1: add set_network_timeout (timoutout = 30) and change
  default keep alive timeout from 2 to 30
- 0.26.4: fix incomplete sending when resuested with connection: close header
- 0.26.3.7: enforce response to HTTP version 1.1 for 1.0 CONNECT
  with 1.0 request
- 0.26.3.5: revert multiworkers
- 0.26.3.2: fix multiworkers
- 0.26.3.1: update making for self-signing certification
- 0.26.3: add skitai.enable_forward
- 0.26.2.1: remove was.promise.render_all (), change method name
  from was.promise.push () to send ()
- 0.26.2: change name from was.aresponse to was.promise
- 0.26.1.1: add skitai.abspath (\*args)
- 0.26.1: fix proxy & proxypass, add was.request.scheme and update examples
- change development status to Beta
- fix Saddlery routing
- disable WWW-Authenticate on websocket protocol
- support CORS (Cross Origin Resource Sharing)
- support PATCH method
- runtime app preferences and add __init__.bootstrap (preference)
- fix route caching
- auto reload sub modules in package directory, if app.use_reloader = True
- new was.request.json ()
- integrated with skitaid package, single app file can contain
  all configure options
- level down developement status to alpha
- fix sqlite3 closing

0.25 (Feb 2017)

- 0.25.7: fix fancy url, non content-type header post/put request
- 0.25.6: add Chameleon_ template engine
- 0.25.5: app.jinja_overlay ()'s default args become jinja2 default
- 0.25.4.8: fix proxy retrying
- 0.25.4 license changed from BSD to MIT, fix websocket init at single thread
- 0.25.3 handler of promise args spec changed, class name is
  changed from AsyncResponse to Promise
- 0.25.2 fix promise exception handling, promise can send streaming chunk data
- 0.25.1 change app.jinja_overlay () default values and number
  of args, remove raw line statement
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
- WEBSOCKET_MULTICAST deprecated, and new WEBSOCKET_GROUPCHAT
  does not create new thread any more

0.23 (Jan 2017)

- ready_producer_fifo only activated when proxy or reverse
  proxy is enabled, default deque will be used
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
- 0.21.3 - add JWT (JSON Web Token) handler, see
  `Skitai WSGI App Engine Daemon`_
- 0.21.2 - applied global/local-transaction-ID to app
  logging: was.log (msg, logtype), was.traceback ()
- 0.21 - change request log format, add global/local-transaction-ID
  to log file for backtrace

0.20 (Dec 2016)

- 0.20.15 - minor optimize asynconnect, I wish
- 0.20.14 - fix Redis connector's threading related error
- 0.20.4 - add Redis connector
- 0.20 - add API Gateway access handler

0.19 (Dec 2016)

- Reengineering was.request methods, fix disk caching

0.18 (Dec 2016)

- 0.18.11 - default content-type of was.post(), was.put() has
  been changed from 'application/x-www-form-urlencoded' to 'application/json'.
  if you use this method currently, you SHOULD change method name
  to was.postform()

- 0.18.7 - response contents caching has been applied to all
  was.request services (except websocket requests).

0.17 (Oct 2016)

- `Skitai WSGI App Engine Daemon`_ is seperated

0.16 (Sep 2016)

- 0.16.20 fix SSL proxy and divide into package for proxy & websocket_handler
- 0.16.19 fix HTTP2 cookie
- 0.16.18 fix handle large request body
- 0.16.13 fix thread locking for h2.Connection
- 0.16.11 fix pushing promise and response on Firefox
- 0.16.8 fix pushing promise and response
- 0.16.6 add several configs to was.app.config for
  limiting post body size from client
- 0.16.5 add method: was.response.hint_promise (uri) for
  sending HTP/2 PUSH PROMISE frame
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
.. _hyper-h2: https://pypi.python.org/pypi/h2
.. _pebble: https://pypi.python.org/pypi/pebble


