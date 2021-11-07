from rs4.annotations import deprecated
from ..wastuff.api import tojson
from ..tasks import tasks
import xmlrpc.client as xmlrpclib
from rs4.misc.producers import file_producer

class Deprecated:
    @deprecated ()
    def render_ei (self, exc_info, format = 0):
        return http_response.catch (format, exc_info)

    @deprecated ()
    def togrpc (self, obj):
        return obj.SerializeToString ()

    @deprecated ()
    def fromgrpc (self, message, obj):
        return message.ParseFromString (obj)

    @deprecated ()
    def tojson (self, obj):
        return tojson (obj)
        # return json.dumps (obj, cls = encoder)

    @deprecated ()
    def toxml (self, obj):
        return xmlrpclib.dumps (obj, methodresponse = False, allow_none = True, encoding = "utf8")

    @deprecated ()
    def fromjson (self, obj):
        if type (obj) is bytes:
            obj = obj.decode ('utf8')
        return json.loads (obj)

    @deprecated ()
    def fromxml (self, obj, use_datetime = 0):
        return xmlrpclib.loads (obj)

    @deprecated ()
    def fstream (self, path, mimetype = 'application/octet-stream'):
        self.response.set_header ('Content-Type',  mimetype)
        self.response.set_header ('Content-Length', str (os.path.getsize (path)))
        return file_producer (open (path, "rb"))

    @deprecated ()
    def jstream (self, obj, key = None):
        self.response.set_header ("Content-Type", "application/json")
        if key:
            # for single skeleton data is not dict
            return self.tojson ({key: obj})
        else:
            return self.tojson (obj)

    @deprecated ()
    def xstream (self, obj, use_datetime = 0):
        self.response.set_header ("Content-Type", "text/xml")
        return self.toxml (obj, use_datetime)

    @deprecated ()
    def gstream (self, obj):
        self.response.set_header ("Content-Type", "application/grpc")
        return self.togrpc (obj)

    @deprecated ('use tasks.then ()')
    def Future (self, req, timeout = 10, **args):
        # deprecated, use tasks.then ()
        if isinstance (req, (list, tuple)):
            raise ValueError ('Future should be single Task')
        return tasks.Future (req, timeout, **args)

    @deprecated ('use was.Tasks.then ()')
    def Futures (self, reqs, timeout = 10, **args):
        if not isinstance (reqs, (list, tuple)):
            raise ValueError ('Futures should be multiple Tasks')
        return tasks.Futures (reqs, timeout, **args)
    future = Future
    futures = Futures
