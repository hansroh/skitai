import json
import sys
from xmlrpc import client
from ..utility import catch
import copy
from datetime import timezone, datetime, date

TZ_LOCAL = datetime.now (timezone.utc).astimezone().tzinfo
TZ_UTC = timezone.utc

class StringDateTimeEncoder (json.JSONEncoder):
	def _to_utc (self, obj):
		try:
			return obj.astimezone (TZ_UTC)
		except ValueError:
			return obj.replace (tzinfo = TZ_LOCAL).astimezone (TZ_UTC)

	def default (self, obj):
		if isinstance (obj, date):
			return str (obj)
		return json.JSONEncoder.default (self, obj)

class DigitTimeEncoder (StringDateTimeEncoder):
	def default (self, obj):
		if isinstance (obj, date):
			return self._to_utc (obj).strftime ('%Y%m%d%H%M%S')
		return json.JSONEncoder.default (self, obj)

class ISODateTimeEncoder (StringDateTimeEncoder):
	def default (self, obj):
		if isinstance (obj, date):
			return self._to_utc (obj).isoformat ()
		return json.JSONEncoder.default (self, obj)

class UNIXEpochDateTimeEncoder (StringDateTimeEncoder):
	def default (self, obj):
		if isinstance (obj, date):
			return self._to_utc (obj).timestamp ()
		return json.JSONEncoder.default (self, obj)

class ISODateTimeWithOffsetEncoder (StringDateTimeEncoder):
	def default (self, obj):
		if isinstance (obj, date):
			return self._to_utc (obj).strftime ('%Y-%m-%d %H:%M:%S+00')
		return json.JSONEncoder.default (self, obj)


class API:
	ENCODER_MAP = {
		'str': StringDateTimeEncoder,
		'iso': ISODateTimeEncoder,
		'unixepoch': UNIXEpochDateTimeEncoder,
		'digit': DigitTimeEncoder,
		'utcoffset': ISODateTimeWithOffsetEncoder
	}

	@classmethod
	def add_custom_encoder (cls, name, encoder):
		cls.ENCODER_MAP [name] = encoder

	def __init__ (self, request, data = None):
		self.request = request # for response typing
		self.data = data or {}
		self.content_type = self.set_content_type ()
		self.data_encoder_class = None

	def set_json_encoder (self, encoder):
		if not encoder:
			return
		if isinstance (encoder, str):
			self.data_encoder_class = self.ENCODER_MAP [encoder]
			return
		self.data_encoder_class = encoder

	def __setitem__ (self, k, v):
		self.set (k, v)

	def __getitem__ (self, k, v = None):
		return self.get (k, v)

	def set (self, k, v):
		self.data [k] = v

	def get (self, k, v = None):
		return self.data.get (k, v)

	def get_content_type (self):
		return self.content_type

	def set_content_type (self):
		content_type = self.request.get_header ("accept", 'application/json')
		if not content_type.startswith ("text/xml"):
			content_type = 'application/json'
		return content_type

	def encode (self, charset):
		return self.to_string ().encode (charset)

	def __str__ (self):
		return self.to_string ()

	def to_string (self):
		if self.content_type.startswith ("text/xml"):
			return client.dumps ((self.data,))
		return json.dumps (self.data, cls = self.data_encoder_class or self.ENCODER_MAP ['utcoffset'], ensure_ascii = False, indent = 2)

	def traceback (self, message = 'exception occured', code = 20000, debug = 'see traceback', more_info = None):
		self.error (message, code, debug, more_info, sys.exc_info ())

	def error (self, message, code = 20000, debug = None, more_info = None, exc_info = None):
		self.data = {}
		self.data ['code'] = code
		self.data ['message'] = message
		if debug:
			self.data ['debug'] = debug
		if more_info:
			self.data ['more_info'] = more_info
		if exc_info:
			self.data ["traceback"] = type (exc_info) is tuple and catch (2, exc_info) or exc_info

	def set_spec (self, app):
		resource_id = self.request.routable ["func_id"]
		routable = copy.deepcopy (self.request.routable)
		del routable ["func_id"]
		routable ["methods"] = list (routable ["methods"])
		props = {"current_request": {}}
		props ["current_request"]["method"] = self.request.method
		props ["current_request"]["version"] = self.request.version
		props ["current_request"]["uri"] = self.request.uri
		props ['routeopt'] = routable
		props ["parameter_requirements"] = app.get_parameter_requirements (resource_id)
		props ['auth_requirements'] = app.get_auth_flags (resource_id)
		props ["doc"] = self.request.routed.__doc__
		props ["id"] = resource_id
		self.data ["__spec__"] = props

		#import pprint
		#pprint.pprint (self.data ["__spec__"])
