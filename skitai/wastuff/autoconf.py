
from rs4 import pathtool
from rs4.termcolor import tc
import os
from distutils.dir_util import copy_tree
import shutil

def _collect_routes (vhost):
    proxies = {}
    if hasattr (vhost, "proxypass_handler"):
        for path, cname in vhost.proxypass_handler.sorted_route_map:
            cluster = vhost.proxypass_handler.clusters [cname [0]]
            targets = []
            for member in cluster.members:
                try:
                    target, weight = member.split ()
                except ValueError:
                    target, weight = member, 1
                weight = int (weight)
                targets.append ((target, weight))

            if path not in proxies:
                proxies [path] = []
            proxies [path].append ((cname [0], targets))

    return vhost.default_handler.filesystem.maps, proxies, vhost.apps.modules

def collect_static (conf, static_root, mounted_points):
    print ("collecting static files...")
    if os.path.isdir (static_root):
        shutil.rmtree (static_root)
    copied = 0
    for path, rscs in sorted (mounted_points.items (), key = lambda x: len (x [0]), reverse = True):
        if conf.get ("media_url") and path.startswith (conf ["media_url"][:-1]):
            print ("- skip media")
            continue
        if not path:
            path = '/'
        for rsc in rscs [::-1]:
            target = static_root + path
            pathtool.mkdir (target)
            r = copy_tree (rsc ['path'], target, update = 1, verbose = 1)
            print (f"- copying static: {tc.primary (rsc ['path'])} into {tc.white (target)}")
            copied += len (r)
    print ("total {} static files collected at {}".format (tc.warn ('{:,}'.format (copied)), tc.info (static_root)))

def generate (project_root, vhost, conf):
    depdir = os.path.join (project_root, 'dep')
    if not os.getenv ('STATIC_ROOT'):
        os.environ ['STATIC_ROOT'] = os.path.join (project_root, 'dep/nginx/.static_files')

    print ("collecting routes...")
    A, B, C = _collect_routes (vhost)
    pathtool.mkdir (depdir)
    collect_static (conf, os.getenv ('STATIC_ROOT'), A)
