import threading
from aquests.client import asynconnect, synconnect
from aquests.client.socketpool import PROTO_CONCURRENT_STREAMS, select_channel
import time
import re
import copy
import random
from rs4 import webtest
from operator import itemgetter
import math
from urllib.parse import unquote
from skitai import PROTO_HTTP, PROTO_HTTPS, PROTO_SYN_HTTP, PROTO_SYN_HTTPS
from aquests.client.asynconnect import ConnectProxy

class TooManyConnections (Exception):
    pass

class AccessPolicy:
    def __init__ (self, roles, ips):
        self.roles = self.to_list (roles)
        self.ips = []
        for ip_mask in self.to_list (ips):
            try: ip, mask = ip_mask.split ("/", 1)
            except ValueError: ip, mask = ip_mask, 32
            else: mask = int (mask)
            pp = math.floor (mask / 8)
            mask_bits = mask % 8
            mask_bit = "1" * mask_bits
            mask_bit += "0" * (8 - mask_bits)
            self.ips.append ((ip.split (".")[:pp], mask, pp, int (mask_bit, 2)))

    def to_list (self, s):
        return list (filter (None, map (lambda x: x.strip (), s.split (","))))

    def has_role (self, roles):
        if not self.roles:
            return roles and True or False
        for role in roles:
            if role in self.roles:
                return True
        return False

    def is_valid_request (self, request):
        if not self.ips:
            return True
        client_ip = request.channel.addr [0]
        for ip, mask, pp, mask_bit in self.ips:
            if mask == 32 and client_ip == ip:
                return True
            client_ip = client_ip.split (".")
            if ip    != client_ip [:pp]:
                continue
            if mask_bit == 0:
                return True
            if int (client_ip [pp]) & mask_bit == mask_bit:
                return True
        return False


class ClusterManager:
    object_timeout = 120
    maintern_interval = 30
    # I cannot sure this is faster
    backend = True
    backend_keep_alive = 10
    use_syn_connection = False
    proxy_class = ConnectProxy

    def __init__ (self, name, cluster, ctype = PROTO_HTTP, access = None, max_conns = 32, logger = None):
        self.logger = logger
        self.lock = threading.RLock ()
        self._name = name
        self.access = access
        self._use_ssl = ctype in (PROTO_HTTPS, PROTO_SYN_HTTPS) and True or False
        self.ctype = ctype
        self.set_class ()
        self._max_conns = max_conns
        self._proto = None
        self._havedeadnode = 0
        self._numget = 0
        self._nummget = 0
        self._clusterlist = []
        self._cluster = {}
        self._last_maintern = time.time ()
        self._close_desires = []
        if cluster:
            self.create_pool (cluster)

    def __len__ (self):
        return len (self._cluster)

    def has_permission (self, request, roles):
        if self.access is None:
            return True
        return self.access.is_valid_request (request) and self.access.has_role (roles)

    def get_name (self):
        return self._name

    def is_ssl_cluster (self):
        return self._use_ssl

    def set_class (self):
        if self.use_syn_connection or self.ctype in (PROTO_SYN_HTTP, PROTO_SYN_HTTPS):
            if self._use_ssl:
                self._conn_class = synconnect.SynSSLConnect
            else:
                self._conn_class = synconnect.SynConnect
        else:
            if self._use_ssl:
                self._conn_class = asynconnect.AsynSSLConnect
            else:
                self._conn_class = asynconnect.AsynConnect

    def status (self):
        info = {}
        cluster = {}
        self.lock.acquire ()
        try:
            try:
                for node in self._cluster:
                    _node = copy.copy (self._cluster [node])
                    _node ["numactives"] = len ([x for x in _node ["connection"] if x.isactive ()])
                    _node ["numconnected"] = len ([x for x in _node ["connection"] if x.isconnected ()])

                    conns = []
                    for asyncon in _node ["connection"]:
                        conn = {
                                "connected": asyncon.isconnected (),
                                "isactive": asyncon.isactive (),
                                "request_count": asyncon.get_request_count (),
                                "event_time": time.asctime (time.localtime (asyncon.event_time)),
                                "zombie_timeout": asyncon.zombie_timeout,
                                "keep_alive": asyncon.keep_alive,
                                "tasks": len (asyncon._tasks),
                            }
                        if hasattr (asyncon, "get_history"):
                            conn ["history"] = asyncon.get_history ()
                        conns.append (conn)

                    _node ["connection"] = conns
                    cluster [str (node)] = _node
                info ["cluster"] = cluster

                actives = len ([x for x in self._close_desires if x.isactive ()])
                connecteds = len ([x for x in self._close_desires if x.isconnected ()])
                info ["close_pending"] = "%d (active: %d, connected: %d)" % (len (self._close_desires), actives, connecteds)
                info ["numget"] = self._numget
                info ["nummget"] = self._nummget
                info ["ssl"] = self.is_ssl_cluster ()


            finally:
                self.lock.release ()
        except:
            self.logger.trace ()

        return info

    def cleanup (self):
        self.lock.acquire ()
        try:
            try:
                for node in list(self._cluster.keys ()):
                    self._cluster [node]["stoped"] = True
                    for asyncon in self._cluster [node]["connection"]:
                        asyncon.disconnect ()
            finally:
                self.lock.release ()
        except:
            self.logger.trace ()

    def get_nodes (self):
        nodes = []
        self.lock.acquire ()
        try:
            try:
                nodes = [k for k, v in list(self._cluster.items ()) if not v ["stoped"]]
            finally:
                self.lock.release ()
        except:
            self.logger.trace ()
        return nodes

    def get_cluster (self):
        return self._cluster

    def parse_member (self, member):
        auth = None
        try:
            userpass, netloc =  member.split ("@", 1)
        except ValueError:
            netloc =    member
        else:
            try:
                user, passwd = userpass.split (":", 1)
            except ValueError:
                user, passwd = userpass, ""
            auth  = (unquote (user), unquote (passwd))
        return auth, netloc

    def create_asyncon (self, member):
        auth, netloc = self.parse_member (member)
        try:
            host, port = netloc.split (":", 1)
            server = (host, int (port))
        except ValueError:
            if not self._use_ssl:
                server    = (netloc, 80)
            else:
                server    = (netloc, 443)
        asyncon = self._conn_class (server, self.lock, self.logger)
        asyncon.set_auth (auth)
        self.backend and asyncon.set_backend (self.backend_keep_alive)
        return server, asyncon # nodeid, asyncon

    def add_node (self, member):
        try:
            member, weight = member.split (" ", 1)
            weight = int (weight)
        except ValueError:
            weight = 1

        node, asyncon = self.create_asyncon (member)

        self.lock.acquire ()
        exists = node in self._cluster
        self.lock.release ()
        if exists:
            self._cluster [node]["weight"] = weight
            return

        _node = {"check": None, "connection": [], "weight": weight, "deadcount": 0, "stoped": False, "deadtotal": 0}
        _node ["connection"] = [asyncon]

        self.lock.acquire ()
        self._cluster [node] = _node
        self._clusterlist.append (node)
        self.lock.release ()

    def remove_node (self, member):
        host, port = member.split (":", 1)
        node = (host, int (port))
        self.lock.acquire ()
        try:
            try:
                if node in self._cluster:
                    self._close_desires += self._cluster [node]["connection"]
                    del self._cluster [node]
                    del self._clusterlist [self._clusterlist.index (node)]
            finally:
                self.lock.release ()
        except:
            self.logger.trace ()

    def switch_node (self, member, stop = False):
        host, port = member.split (":", 1)
        node = (host, int (port))
        self.lock.acquire ()
        try:
            try:
                if node in self._cluster:
                    self._cluster [node]["stoped"] = stop
                    if stop is False:
                        self._cluster [node]["deadcount"] = 0
                        self._cluster [node]["check"] = None

            finally:
                self.lock.release ()
        except:
            self.logger.trace ()

    def create_pool (self, cluster):
        for member in cluster:
            self.add_node (member)

    def report (self, asyncon, well_functioning):
        node = asyncon.address
        self.lock.acquire ()
        try:
            try:
                cluster = self._cluster
                if not well_functioning:
                    if cluster [node]["deadcount"] < 10:
                        recheck = 60
                    else:
                        recheck = 60 * 10
                    cluster [node]["check"] = time.time () + recheck
                    cluster [node]["deadcount"] += 1
                    cluster [node]["deadtotal"] += 1

                else:
                    cluster [node]["deadcount"] = 0
                    cluster [node]["check"] = None

            finally:
                self.lock.release ()

        except:
            self.logger.trace ()

    def maintern (self):
        try:
            # close unused sockets
            for _node in list(self._cluster.values ()):
                survived = []
                for asyncon in _node ["connection"]:
                    if not hasattr (asyncon, "maintern"):
                        continue
                    if asyncon.maintern (self.object_timeout):
                        asyncon.handler = None # break back ref.
                    else:
                        survived.append (asyncon)

                if len (survived) == 0:
                    # at least 1 must be survived for duplicating
                    _node ["connection"] = _node ["connection"][:1]
                elif len (_node ["connection"]) != len (survived):
                    _node ["connection"] = survived

            # checking dead nodes
            if self._havedeadnode:
                for node in [k for k, v in list(self._cluster.items ()) if v ["check"] is not None and not v ["stoped"]]:
                    if time.time () > self._cluster [node]["check"]:
                        self._cluster [node]["check"] = None

            # closing removed mode's sockets
            if self._close_desires:
                cannot_closes = []
                for asyncon in self._close_desires:
                    if asyncon.isactive ():
                        cannot_closes.append (asyncon)
                    else:
                        asyncon.disconnect ()
                self._close_desires = cannot_closes

        except:
            self.logger.trace ()

    def get (self, specific = None, index = -1):
        asyncon = None

        with self.lock:
            self._numget += 1
            if time.time () - self._last_maintern > self.maintern_interval:
                self._last_maintern = time.time ()
                self.maintern ()

            if specific:
                nodes = [specific]

            elif index != -1:
                try:
                    nodes = [self._clusterlist [index]]
                except IndexError:
                    nodes = [self._clusterlist [-1]]

            else:
                nodes = [k for k, v in list(self._cluster.items ()) if v ["check"] is None and not v ["stoped"]]
                self._havedeadnode = len (self._cluster) - len (nodes)
                if not nodes:
                    #assume all live...
                    nodes = [k for k, v in list(self._cluster.items ()) if not v ["stoped"]]

            cluster = []
            for node in nodes:
                avails = [x for x in self._cluster [node]["connection"] if not x.isactive ()]
                if self._proto and self._proto in PROTO_CONCURRENT_STREAMS:
                    # socket load-balancing
                    selected = select_channel (avails)
                    avail = selected and [selected] or []

                if not avails:
                    continue

                weight = self._cluster [node]["weight"]
                actives = weight - len (avails)

                if actives == 0:
                    capability = 1.0
                else:
                    capability = 1.0 - (actives / float (weight))

                avail = avails [0]
                cluster.append ((avail, capability, weight))

            if cluster:
                random.shuffle (cluster) # load balancing between same weighted members
                cluster.sort (key = itemgetter(1, 2), reverse = True)
                asyncon = cluster [0][0]

            else:
                t = [(len (self._cluster [node]["connection"]), node) for node in nodes]
                t.sort ()
                current_conns, node = t [0]
                if current_conns < self._max_conns:
                    asyncon = self._cluster [node]["connection"][0].duplicate ()
                    self._cluster [node]["connection"].append (asyncon)
                else:
                    asyncon = self.proxy_class (random.choice (self._cluster [node]["connection"]))

            asyncon.set_active (True)

        if self._proto is None:
            self._proto = asyncon.get_proto ()

        return asyncon

    def sortfunc (self, a, b):
        r = b [1] - a [1]
        if r != 0: return r
        return b [2] - a [2]

    def get_endpoints (self):
        endpoints = []
        scheme = self._use_ssl and "https" or "http"
        for node, config in self._cluster.items ():
            port = node [1]
            ep = "{}://{}".format (scheme, node [0])
            if not (scheme == "https" and port == 443 or scheme == "http" and port == 80):
                ep += ":{}".format (port)
            endpoints.append (webtest.Target (ep))
        return endpoints
