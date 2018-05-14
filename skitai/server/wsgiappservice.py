import os, sys
import time
import tempfile
from hmac import new as hmac
from hashlib import sha1
import json
import xmlrpc.client as xmlrpclib
import base64
import pickle
from multiprocessing import RLock
import random
import threading
from aquests.lib import pathtool, logger, jwt
from aquests.lib.producers import simple_producer, file_producer
from aquests.lib.athreads import trigger
from aquests.protocols.smtp import composer
from aquests.protocols.http import http_date
import inspect
from skitai import __version__, WS_EVT_OPEN, WS_EVT_CLOSE, WS_EVT_INIT
from skitai import DB_PGSQL, DB_SQLITE3, DB_REDIS, DB_MONGODB
from skitai import lifetime
from skitai.server.handlers import api_access_handler, vhost_handler
from .rpc import cluster_manager, cluster_dist_call
from .dbi import cluster_manager as dcluster_manager, cluster_dist_call as dcluster_dist_call
from . import server_info
from . import http_response
from .wastuff.promise import Promise, _Method
from .wastuff.triple_logger import Logger
from .wastuff import django_adaptor
from .wastuff.api import DateEncoder

if os.name == "nt":
	TEMP_DIR =  os.path.join (tempfile.gettempdir(), "skitai-gentemp")
else:
	TEMP_DIR = "/var/tmp/skitai-gentemp"		
pathtool.mkdir (TEMP_DIR)

class JWTUser:
	def __init__ (self, claims):
		self.__claims = claims
	
	@property
	def name (self):
		return self.__claims ["username"]
    	
	def __getattr__ (self, attr):
		return self.__claims.get (attr)
            
	def __str__ (self):
		return self.name


class WAS:
	version = __version__	
	objects = {}	
	_luwatcher = None
	
	lock = RLock ()
	init_time = time.time ()	
	
	# application friendly methods -----------------------------------------
	
	@classmethod
	def register (cls, name, obj):
		if hasattr (cls, name):
			raise AttributeError ("server object `%s` is already exists" % name)
		cls.objects [name] = obj
		setattr (cls, name, obj)
	
	@classmethod
	def unregister (cls, name):
		del cls.objects [name]
		return delattr (cls, name)
		
	@classmethod
	def add_handler (cls, back, handler, *args, **karg):
		h = handler (cls, *args, **karg)
		if hasattr (cls, "httpserver"):
			cls.httpserver.install_handler (h, back)
		return h
						
	@classmethod
	def add_cluster (cls, clustertype, clustername, clusterlist, ssl = 0, access = []):
		if clustertype and clustertype [0] == "*":
			clustertype = clustertype [1:]
		ssl = 0
		if ssl in (1, True, "1", "yes") or clustertype in ("https", "wss", "grpcs", "rpcs"):
			ssl = 1
		if type (clusterlist) is str:
			clusterlist = [clusterlist]	

		if clustertype and "*" + clustertype in (DB_PGSQL, DB_SQLITE3, DB_REDIS, DB_MONGODB):
			cluster = dcluster_manager.ClusterManager (clustername, clusterlist, "*" + clustertype, access, cls.logger.get ("server"))
			cls.clusters_for_distcall [clustername] = dcluster_dist_call.ClusterDistCallCreator (cluster, cls.logger.get ("server"))
		else:
			cluster = cluster_manager.ClusterManager (clustername, clusterlist, ssl, access, cls.logger.get ("server"))
			cls.clusters_for_distcall [clustername] = cluster_dist_call.ClusterDistCallCreator (cluster, cls.logger.get ("server"), cls.cachefs)
		cls.clusters [clustername] = cluster
	
	@property
	def timestamp (self):
		return int (time.time () * 1000) 
	
	@property
	def uniqid (self):
		return "{}{}".format (self.timestamp, self.gentemp () [-7:])
		
	def __dir__ (self):
		return self.objects.keys ()
	
	def __str__ (self):
		return "skitai was for {}".format (threading.currentThread ())
					
	def __detect_cluster (self, clustername):
		try: 
			clustername, uri = clustername.split ("/", 1)
		except ValueError:
			clustername, uri = clustername, ""
		if clustername [0] == "@":
			clustername = clustername [1:]
		
		try: 
			return self.clusters_for_distcall ["{}:{}".format (clustername, self.app.app_name)], "/" + uri			
		except KeyError:
			return self.clusters_for_distcall [clustername], "/" + uri
		
	def in__dict__ (self, name):
		return name in self.__dict__
	
	def _clone (self, disable_aquests = False):
		new_was = self.__class__ ()
		for k, v in self.__dict__.items ():
			setattr (new_was, k, v)	
		if disable_aquests:
			new_was.VALID_COMMANDS = []
		return new_was
	
	# mehiods remap ------------------------------------------------
			
	VALID_COMMANDS = [
		"options", "trace", "upload",
		"get", "getjson",
		"delete", "deletejson",
		"post", "postjson",
		"put", "putjson",
		"patch", "patchjson",
		"rpc", "jsonrpc", "grpc", "ws", "wss", 
		"db", "postgresql", "sqlite3", "redis", "mongodb", "backend",		
	]
	def __getattr__ (self, name):
		# method magic		
		if name in self.VALID_COMMANDS:
			return _Method (self._call, name, inspect.stack() [1])
		
		if self.in__dict__ ("app"): # saddle app			
			attr = self.app.create_on_demand (self, name)
			if attr:
				setattr (self, name, attr)
				return attr
		
		try:
			return self.objects [name]
		except KeyError:	
			raise AttributeError ("'was' hasn't attribute '%s'" % name)	
	
	def _call (self, method, args, karg):
		# was.db, 		was.get, 			was.post,			was.put, ...
		# was.db.lb, 	was.get.lb,		was.post.lb,	was.put.lb, ...
		# was.db.map,	was.get.map,	was.post.map,	was.put.map, ...

		uri = None
		if args:		uri = args [0]
		elif karg:	uri = karg.get ("uri", "")
		if not uri:	raise AssertionError ("Missing param uri or cluster name")

		try: 
			command, fn = method.split (".")
		except ValueError: 
			command = method
			if uri [0] == "@": 
				fn = "lb"
			else:
				fn = (command in ("db", "postgresql", "sqlite3", "redis", "mongodb", "backend") and "db" or "rest")

		if fn == "map" and not hasattr (self, "threads"):
			raise AttributeError ("Cannot use Map-Reduce with Single Thread")
		
		if command == "db":
			return getattr (self, "_d" + fn) (*args, **karg)			
		elif command in ("postgresql", "sqlite3", "redis", "mongodb", "backend"):
			return getattr (self, "_a" + fn) ("*" + command, *args, **karg)					
		else:	
			return getattr (self, "_" + fn) (command, *args, **karg)
	
	# TXN -----------------------------------------------
	
	def txnid (self):
		return "%s/%s" % (self.request.gtxid, self.request.ltxid)
	
	def rebuild_header (self, header = None):
		if not header:
			nheader = {}
		elif type (header) is list:
			nheader = {}			
			for k, v in header:
				nheader [k] = v
		else:
			nheader = header
					
		nheader ["X-Gtxn-Id"] = self.request.get_gtxid ()
		nheader ["X-Ltxn-Id"] = self.request.get_ltxid (1)
		return nheader
	
	# async requests -----------------------------------------------
		
	def _rest (self, method, uri, data = None, auth = None, headers = None, meta = None, use_cache = True, filter = None, callback = None, timeout = 10, caller = None):
		return self.clusters_for_distcall ["__socketpool__"].Server (uri, data, method, self.rebuild_header (headers), auth, meta, use_cache, False, filter, callback, timeout, caller)
	
	def _crest (self, mapreduce = False, method = None, uri = None, data = None, auth = None, headers = None, meta = None, use_cache = True, filter = None, callback = None, timeout = 10, caller = None):
		cluster, uri = self.__detect_cluster (uri)
		return cluster.Server (uri, data, method, self.rebuild_header (headers), auth, meta, use_cache, mapreduce, filter, callback, timeout, caller)
				
	def _lb (self, *args, **karg):
		return self._crest (False, *args, **karg)
		
	def _map (self, *args, **karg):
		return self._crest (True, *args, **karg)
	
	def _bind_sqlphile (self, dbo):
		try:
			app_sqlphile = self.sql
		except AttributeError:
			return dbo	
		return app_sqlphile.new (dbo)
			
	def _ddb (self, server, dbname = "", auth = None, dbtype = DB_PGSQL, meta = None, use_cache = True, filter = None, callback = None, timeout = 10, caller = None):
		dbo = self.clusters_for_distcall ["__dbpool__"].Server (server, dbname, auth, dbtype, meta, use_cache, False, filter, callback, timeout, caller)
		if dbtype in (DB_PGSQL, DB_SQLITE3):
			return self._bind_sqlphile (dbo)
		return dbo
	
	def _cddb (self, mapreduce = False, clustername = None, meta = None, use_cache = True, filter = None, callback = None, timeout = 10, caller = None):
		if mapreduce and callback: raise RuntimeError ("Cannot use callback with Map-Reduce")
		cluster = self.__detect_cluster (clustername) [0]
		dbo = cluster.Server (None, None, None, None, meta, use_cache, mapreduce, filter, callback, timeout, caller)
		if cluster.cluster.dbtype in (DB_PGSQL, DB_SQLITE3):
			return self._bind_sqlphile (dbo)
		return dbo	
	
	def _dlb (self, *args, **karg):
		return self._cddb (False, *args, **karg)
	
	def _dmap (self, *args, **karg):
		return self._cddb (True, *args, **karg)
	
	def _adb (self, dbtype, server, dbname = "", auth = None, meta = None, use_cache = True, filter = None, callback = None, timeout = 10, caller = None):
		return self._ddb (server, dbname, auth, dbtype, meta, use_cache, filter, callback, timeout, caller)
	
	def _alb (self, dbtype, *args, **karg):
		return self._cddb (False, *args, **karg)
	
	def _amap (self, dbtype, *args, **karg):
		return self._cddb (True, *args, **karg)
	
	# system functions ----------------------------------------------
		
	def log (self, msg, category = "info", at = "app"):
		self.logger (at, msg, "%s:%s" % (category, self.txnid ()))
		
	def traceback (self, id = "", at = "app"):
		if not id:
			id = self.txnid ()
		self.logger.trace (at, id)
	
	@property
	def tempfile (self):
		return self.gentemp () 
	
	def gentemp (self):
		return os.path.join (TEMP_DIR, next (tempfile._get_candidate_names()))
	
	# -- only allpy to current worker process
	def status (self, flt = None, fancy = True):		
		return server_info.make (self, flt, fancy)
	
	def restart (self, timeout = 0):
		lifetime.shutdown (3, timeout)
	
	def shutdown (self, timeout = 0):
		lifetime.shutdown (0, timeout)
	
	# URL builders -------------------------------------------------
	def urlfor (self, thing, *args, **karg):
		# override with resource default args
		if not isinstance (thing, str) or thing.startswith ("/") or thing.find (":") == -1:
			return self.app.urlfor (thing, *args, **karg)		
		return self.apps.urlfor (thing, *args, **karg)	
	ab = urlfor
	
	def partial (self, thing, **karg):
		# override with current args
		karg ["__defaults__"] = self.request.args
		return self.ab (thing, **karg)
	
	def baseurl (self, thing):
		# resource path info without parameters
		return self.ab (thing, __resource_path_only__ = True)
	basepath = baseurl
	
	# response helpers --------------------------------------------
		
	def render (self, template_file, _do_not_use_this_variable_name_ = {}, **karg):
		return self.app.render (self, template_file, _do_not_use_this_variable_name_, **karg)
	
	REDIRECT_TEMPLATE =  (
		"<html><head><title>%s</title></head>"
		"<body><h1>%s</h1>"
		"This document may be found " 
		'<a HREF="%s">here</a></body></html>'
	)
	def redirect (self, url, status = "302 Object Moved", body = None, headers = None):
		redirect_headers = [
			("Location", url), 
			("Cache-Control", "max-age=0"), 
			("Expires", http_date.build_http_date (time.time ()))
		]
		if type (headers) is list:
			redirect_headers += headers
		if not body:
			body = self.REDIRECT_TEMPLATE % (status, status, url)			
		return self.response (status, body, redirect_headers)
	
	def promise (self, handler, **karg):
		self.response.set_streaming ()
		return Promise (self, handler, **karg)
	
	def email (self, subject, snd, rcpt):
		if composer.Composer.SAVE_PATH is None:
			composer.Composer.SAVE_PATH = os.path.join ("/var/tmp/skitai/default", "smtpda", "mail", "spool")
			pathtool.mkdir (composer.Composer.SAVE_PATH)
		return composer.Composer (subject, snd, rcpt)
	
	# event -------------------------------------------------
	
	def broadcast (self, event, *args, **kargs):
		return self.apps.bus.emit (event, self, *args, **kargs)
	
	def setlu (self, name, *args, **karg):
		self._luwatcher.set (name, time.time (), karg.get ("x_ignore", False))
		self.broadcast (name, *args, **karg)			
		
	def getlu (self, *names):
		mtimes = []
		for name in names:
			mtime = self._luwatcher.get (name, self.init_time)
			mtimes.append (mtime)
		return max (mtimes)
	
	# JWT token --------------------------------------------------
	def mkjwt (self, claim, alg = "HS256"):
		return jwt.gen_token (self.app.salt, claim, alg)
	
	def dejwt (self, token):		
		try: 
			claims = jwt.get_claim (self.app.salt, token)
		except (TypeError, ValueError): 
			return	
		if claims is None:
			return
		if "username" in claims:
			self.request.user = JWTUser (claims)
		return claims
		
	# simple/session token  ----------------------------------------
	def _unserialize (self, string):
		def adjust_padding (s):
			paddings = 4 - (len (s) % 4)
			if paddings != 4:
				s += ("=" * paddings)
			return s
		
		string = string.replace (" ", "+")
		try:
			base64_hash, data = string.split('?', 1)
		except ValueError:
			return	
		client_hash = base64.b64decode(adjust_padding (base64_hash))
		data = base64.b64decode(adjust_padding (data))
		mac = hmac (self.app.salt, None, sha1)		
		mac.update (data)
		if client_hash != mac.digest():
			return
		return pickle.loads (data)
	
	def mktoken (self, obj, timeout = 1200, session_key = None):
		wrapper = {
			'object': obj,
			'timeout': time.time () + timeout
		}
		if session_key:
			token = hex (random.getrandbits (64))
			tokey = '_{}_token'.format (session_key)
			wrapper ['_session_token'] = (tokey, token)
			self.session [tokey] = token
			
		data = pickle.dumps (wrapper, 1)
		mac = hmac (self.app.salt, None, sha1)
		mac.update (data)
		return (base64.b64encode (mac.digest()).strip().rstrip (b'=') + b"?" + base64.b64encode (data).strip ().rstrip (b'=')).decode ("utf8")
	token = mktoken
	
	def detoken (self, string):
		wrapper = self._unserialize (string)
		if not wrapper:
			return 
		
		# validation with session
		tokey = None
		has_error = False
		if wrapper ['timeout']  < time.time ():
			has_error = True

		if not has_error:
			session_token = wrapper.get ('_session_token')
			if session_token:
				# verify with session				
				tokey, token = session_token	
				if token != self.session.get (tokey):
					has_error = True
					
		if has_error:
			if tokey:
				del self.session [tokey]
			return
		
		obj = wrapper ['object']
		return obj
	
	def rmtoken (self, string):
		wrapper = self._unserialize (string)
		session_token = wrapper.get ('_session_token')
		if not session_token:
			return
		tokey, token = session_token
		if not self.session.get (tokey):
			return
		del self.session [tokey]
		
	# CSRF token ------------------------------------------------------	
	CSRF_NAME = "_csrf_token"
	@property
	def csrf_token (self):
		if self.CSRF_NAME not in self.session:
			self.session [self.CSRF_NAME] = hex (random.getrandbits (64))
		return self.session [self.CSRF_NAME]

	@property
	def csrf_token_input (self):
		return '<input type="hidden" name="{}" value="{}">'.format (self.CSRF_NAME, self.csrf_token)
	
	def csrf_verify (self, keep = False):
		if not self.request.args.get (self.CSRF_NAME):
			return False
		token = self.request.args [self.CSRF_NAME]
		if self.csrf_token == token:
			if not keep:
				del self.session [self.CSRF_NAME]
			return True
		return False
	
	# proxy & adaptor  -----------------------------------------------
	@property
	def sql (self):
		return self.app.sqlphile
	
	@property
	def django (self):
		if hasattr (self.request, "django"):
			return self.request.django
		self.request.django = django_adaptor.request (self)
		return self.request.django
	
	# websocket methods for generic WSGI containers -----------------------------
	
	def wsconfig (self, spec, timeout = 60, encoding = "text"):
		self.env ["websocket.config"] = (spec, timeout, encoding)
		return ""
		
	def wsinit (self):
		return self.env.get ('websocket.event') == WS_EVT_INIT
	
	def wsopened (self):
		return self.env.get ('websocket.event') == WS_EVT_OPEN
	
	def wsclosed (self):
		return self.env.get ('websocket.event') == WS_EVT_CLOSE
	
	def wshasevent (self):
		return self.env.get ('websocket.event')
	
	def wsclient (self):
		return self.env.get ('websocket.client')	
			
	# will be deprecated --------------------------------------------------	
	
	def togrpc (self, obj):
		return obj.SerializeToString ()
	
	def fromgrpc (self, message, obj):
		return message.ParseFromString (obj)
		
	def tojson (self, obj):
		return json.dumps (obj, cls = DateEncoder)
		
	def toxml (self, obj):
		return xmlrpclib.dumps (obj, methodresponse = False, allow_none = True, encoding = "utf8")	
	
	def fromjson (self, obj):
		if type (obj) is bytes:
			obj = obj.decode ('utf8')
		return json.loads (obj)
	
	def fromxml (self, obj, use_datetime = 0):
		return xmlrpclib.loads (obj)
	
	def fstream (self, path, mimetype = 'application/octet-stream'):	
		self.response.set_header ('Content-Type',  mimetype)
		self.response.set_header ('Content-Length', str (os.path.getsize (path)))	
		return file_producer (open (path, "rb"))
			
	def jstream (self, obj, key = None):
		self.response.set_header ("Content-Type", "application/json")
		if key:
			# for single skeleton data is not dict
			return self.tojson ({key: obj})
		else:
			return self.tojson (obj)		
	
	def xstream (self, obj, use_datetime = 0):			
		self.response.set_header ("Content-Type", "text/xml")
		return self.toxml (obj, use_datetime)
	
	def gstream (self, obj):
		self.response.set_header ("Content-Type", "application/grpc")
		return self.togrpc (obj)
	
	def render_ei (self, exc_info, format = 0):
		return http_response.catch (format, exc_info)
		