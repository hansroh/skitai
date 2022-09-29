
from rs4 import pathtool
from rs4.termcolor import tc
import os
import sys
from distutils.dir_util import copy_tree
import shutil
import requests
import time

NAMES = set ("Shawn April Derek Kathryn Kristin Chad Jenna Tara Maria Krystal Jared Anna Edward Julie Peter Holly Marcus Kristina Natalie Jordan Victoria Jacqueline Corey Keith Monica Juan Donald Cassandra Meghan Joel Shane Phillip Patricia Brett Ronald Catherine George Antonio Cynthia Stacy Kathleen Raymond Carlos Brandi Douglas Nathaniel Ian Craig Brandy Alex Valerie Veronica Cory Whitney Gary Derrick Philip Luis Diana Chelsea Leslie Caitlin Leah Natasha Erika Casey Latoya Erik Dana Victor Brent Dominique Frank Brittney Evan Gabriel Julia Candice Karen Melanie Adrian Stacey Margaret Sheena Wesley Vincent Alexandra Katrina Bethany Nichole Larry Jeffery Curtis Carrie Todd Blake Christian Randy Dennis Alison Michael Christopher Jessica Matthew Ashley Jennifer Joshua Amanda Daniel David James Robert John Joseph Andrew Ryan Brandon Jason Justin Sarah William Jonathan Stephanie Brian Nicole Nicholas Anthony Heather Eric Elizabeth Adam Megan Melissa Kevin Steven Thomas Timothy Christina Kyle Rachel Laura Lauren Amber Brittany Danielle Richard Kimberly Jeffrey Amy Crystal Michelle Tiffany Jeremy Benjamin Mark Emily Aaron Charles Rebecca Jacob Stephen Patrick Sean Erin Zachary Jamie Kelly Samantha Nathan Sara Dustin Paul Angela Tyler Scott Katherine Andrea Gregory Erica Mary Travis Lisa Kenneth Bryan Lindsey Kristen Jose Alexander Jesse Katie Lindsay Shannon Vanessa Courtney Christine Alicia Cody Allison Bradley Samuel".split ())
NAMES = [name.lower () for name in NAMES]

REOMTE_REPO = "https://gitlab.com/skitai/skitai-dep/-/raw/master"
LOCAL_REPO = os.path.join (os.path.dirname (__file__), 'templates')

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

def repl (d, conf):
    d = d.replace ("skitai-dep", conf ["name"])
    d = d.replace ("/hansroh/", '/')
    return d

def get_template_remote (conf, remote, local):
    if not os.path.isfile (local):
        print (f"- skip {tc.info (remote)}")

    pathtool.mkdir (os.path.dirname (local))
    with requests.get (f"{REOMTE_REPO}/{remote}") as r:
        d = repl (r.text, conf)
        with open (local, 'w') as f:
            f.write (d)

    if local [-3:] == ".sh":
        os.chmod (local, 0o744)
    print (f"- wirting {tc.info (remote)}")
    time.sleep (1)

def get_template (conf, remote, local):
    if os.path.isfile (local):
        print (f"- skip {tc.info (remote)}")
        return

    pathtool.mkdir (os.path.dirname (local))
    with open (f"{LOCAL_REPO}/{remote}") as r:
        d = repl (r.read (), conf)
        with open (local, 'w') as f:
            f.write (d)

    if local [-3:] == ".sh":
        os.chmod (local, 0o744)
    print (f"- wirting {tc.info (remote)}")


UPSTREAMS = """
limit_conn_zone $binary_remote_addr zone=ddos_conn:10m;
limit_req_zone $binary_remote_addr zone=ddos_req:10m rate=20r/s;
limit_req_zone $binary_remote_addr zone=app:10m rate=100r/m;

limit_conn ddos_conn 10;
limit_req zone=ddos_req burst=40 nodelay;
"""

UPSTREAM = """
upstream %s {
    zone backend 64k;
    least_conn;
%s
    keepalive 1200;
}
"""

LOCATIONS = """
location / {
    try_files $uri @backend;
}

location @backend {
    proxy_pass http://backend;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    add_header X-Backend "skitai";

    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "Upgrade";
    proxy_read_timeout 60;
}
"""

LOCATION_PROXY = """
location %s {
    proxy_pass http://%s;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
"""

def configure_nginx (conf, bakends, depdir, project_root):
    name = conf ['name']
    nginxdir = os.path.join (depdir, 'nginx', 'conf.d')
    pathtool.mkdir (os.path.join (nginxdir, 'include'))

    print ("configuring nginx...")
    get_template (conf, "dep/nginx/conf.d/include/header.conf", os.path.join (depdir, "nginx/conf.d/include/header.conf"))
    get_template (conf, "dep/nginx/conf.d/default.conf", os.path.join (depdir, "nginx/conf.d/default.conf"))

    print ("- writing {}".format (tc.info ("dep/nginx/conf.d/include/upstream.conf")))
    upstreams = []
    with open (os.path.join (nginxdir, 'include', 'upstreams.conf'), 'w') as f:
        f.write (UPSTREAMS)
        f.write (UPSTREAM % ('backend', "    server {}:{};".format (name, conf.get ('port', 5000))))
        for path, rscs in sorted (bakends.items (), key = lambda x: len (x [0])):
            if not path:
                path = '/'
            for cname, rsc in rscs:
                print (f'  - {cname} {rsc}')
                servers = []
                for member, weight in rsc:
                    servers.append ("    server {} weight={};".format (member, weight))
            f.write (UPSTREAM % (cname, '\n'.join (servers)))
            upstreams.append ((path, cname))

    print ("- writing {}".format (tc.info ("dep/nginx/conf.d/include/routes.conf")))
    with open (os.path.join (nginxdir, 'include', 'routes.conf'), 'w') as f:
        for path, cname in upstreams:
            print (f'  - {path} mounted to {cname}')
            f.write (LOCATION_PROXY % (path, cname))
        if conf.get ("media_url"):
            print ('  - /var/www/pub mounted to {media_url}'.format (**conf))
            f.write ("location %s {\n    alias /var/www/pub;\n}\n" % conf ["media_url"][:-1])
        f.write (LOCATIONS)

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
            print (f"- copying static: {rsc ['path'].replace ('/home/ubuntu', '~')}")
            copied += len (r)
    print ("total {} static files collected at {}".format (tc.warn ('{:,}'.format (copied)), tc.info (static_root)))

def from_template (conf, depdir, project_root):
    build_files = []
    build_files += [ f for f in os.listdir (os.path.join (LOCAL_REPO, "dep"))  if f.endswith ('.Dockerfile') ]
    build_files += [ f for f in os.listdir (os.path.join (LOCAL_REPO, "dep"))  if f.endswith ('.sh') ]
    build_files += [ f for f in os.listdir (os.path.join (LOCAL_REPO, "dep"))  if f.endswith ('.yml') ]
    for f in build_files:
        get_template (conf, f"dep/{f}", os.path.join (depdir, f))

    docker_files = [
        "include/telegram.py", "include/wait-for-it.sh",
        "build.sh", "README.md"
    ]
    docker_files += [ f'Dockerfiles/{f}' for f in os.listdir (os.path.join (LOCAL_REPO, "dep/docker/Dockerfiles")) ]
    for f in docker_files:
        get_template (conf, f"dep/docker/{f}", os.path.join (depdir, f"docker/{f}"))

    terraform_files = [".gitignore"]
    terraform_files += [ f'cloud-infra/{f}' for f in os.listdir (os.path.join (LOCAL_REPO, "dep/terraform/cloud-infra")) if f.endswith ('.tf') ]
    terraform_files += [ f'ecs-cluster/{f}' for f in os.listdir (os.path.join (LOCAL_REPO, "dep/terraform/ecs-cluster")) if f.endswith ('.tf') ]
    terraform_files += [ f'ecs-cluster/policies/{f}' for f in os.listdir (os.path.join (LOCAL_REPO, "dep/terraform/ecs-cluster/policies")) if f.endswith ('.json') ]
    terraform_files += [ f for f in os.listdir (os.path.join (LOCAL_REPO, "dep/terraform")) if f.endswith ('.tf') ]
    for f in terraform_files:
        get_template (conf, f"dep/terraform/{f}", os.path.join (depdir, f"terraform/{f}"))

    if "/.dep" in depdir:
        get_template (conf, ".gitlab-ci.yml", os.path.join (depdir, ".gitlab-ci.yml"))
        get_template (conf, "ctn.sh", os.path.join (depdir, "ctn.sh"))
    else:
        get_template (conf, ".gitlab-ci.yml", os.path.join (project_root, ".gitlab-ci.yml"))
        get_template (conf, "ctn.sh", os.path.join (project_root, "ctn.sh"))


def generate (project_root, vhost, conf, static_only = False):
    depdir = os.path.join (project_root, 'dep')
    if not os.getenv ('STATIC_ROOT'):
        os.environ ['STATIC_ROOT'] = os.path.join (project_root, 'dep/nginx/.static_root')
    assert conf ['name'], 'service name required, add skitai.run (name=NAME)'

    name = conf ['name']
    if not conf.get ('media_path'):
        conf ['media_url'] = None
        conf ['media_path'] = f'/home/ubuntu/.skitai/{name}/pub'
    conf ['media_volume_path'] = os.path.join (f'/home/ubuntu/.skitai')
    conf ['port'] = conf.get ('port', 5000)

    print ("collecting routes to serve with Nginx...")
    A, B, C = _collect_routes (vhost)
    pathtool.mkdir (depdir)

    collect_static (conf, os.getenv ('STATIC_ROOT'), A)
    if static_only:
        return

    if os.path.exists (os.path.join (depdir, ".template")):
        depdir = os.path.join (project_root, '.dep')
        print ("this is {}, and autoconf will be simulated at {}".format (tc.yellow ("template project"), tc.error (depdir)))
        if os.path.isdir (depdir):
            shutil.rmtree (depdir)
        pathtool.mkdir (depdir)

    configure_nginx (conf, B, depdir, project_root)
    from_template (conf, depdir, project_root)

    print ("configurations generated at {}".format (tc.blue (depdir)))
