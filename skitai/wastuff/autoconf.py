
from rs4 import pathtool
from rs4.termcolor import tc
import os
import sys
from distutils.dir_util import copy_tree

NAMES = set ("Shawn April Derek Kathryn Kristin Chad Jenna Tara Maria Krystal Jared Anna Edward Julie Peter Holly Marcus Kristina Natalie Jordan Victoria Jacqueline Corey Keith Monica Juan Donald Cassandra Meghan Joel Shane Phillip Patricia Brett Ronald Catherine George Antonio Cynthia Stacy Kathleen Raymond Carlos Brandi Douglas Nathaniel Ian Craig Brandy Alex Valerie Veronica Cory Whitney Gary Derrick Philip Luis Diana Chelsea Leslie Caitlin Leah Natasha Erika Casey Latoya Erik Dana Victor Brent Dominique Frank Brittney Evan Gabriel Julia Candice Karen Melanie Adrian Stacey Margaret Sheena Wesley Vincent Alexandra Katrina Bethany Nichole Larry Jeffery Curtis Carrie Todd Blake Christian Randy Dennis Alison Michael Christopher Jessica Matthew Ashley Jennifer Joshua Amanda Daniel David James Robert John Joseph Andrew Ryan Brandon Jason Justin Sarah William Jonathan Stephanie Brian Nicole Nicholas Anthony Heather Eric Elizabeth Adam Megan Melissa Kevin Steven Thomas Timothy Christina Kyle Rachel Laura Lauren Amber Brittany Danielle Richard Kimberly Jeffrey Amy Crystal Michelle Tiffany Jeremy Benjamin Mark Emily Aaron Charles Rebecca Jacob Stephen Patrick Sean Erin Zachary Jamie Kelly Samantha Nathan Sara Dustin Paul Angela Tyler Scott Katherine Andrea Gregory Erica Mary Travis Lisa Kenneth Bryan Lindsey Kristen Jose Alexander Jesse Katie Lindsay Shannon Vanessa Courtney Christine Alicia Cody Allison Bradley Samuel".split ())
NAMES = [name.lower () for name in NAMES]

def _collect_routes (vhost):
    proxies = {}
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

NGINX = """
include conf.d/include/upstreams.conf;
server {
    listen 80;
    listen [::]:80;
    server_name _;
    include conf.d/include/header.conf;
    include conf.d/include/routes.conf;
}
"""

HEADER = """
proxy_http_version 1.1;
proxy_set_header Connection "";

root /var/www/html;
index index.html index.htm;
access_log /var/log/nginx/access.log;

reset_timedout_connection on;
client_body_timeout 10s;
client_header_timeout 10s;
send_timeout 10s;

keepalive_timeout 2s;
client_max_body_size 2000M;

proxy_buffer_size 4k;
proxy_buffers 4 128k;
proxy_busy_buffers_size 128k;
"""

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

DOCKER_FILE_NGINX = """
FROM nginx

COPY ./dep/nginx/conf.d /etc/nginx/conf.d
COPY ./dep/nginx/.static_root /var/www/html
"""

DOCKER_COMPOSE = """
version: '2'
services:
  %s:
    imasge: %s
    build:
      context: ../
      dockerfile: dep/Dockerfile
    user: ubuntu
    ports:
      - "%s:%s"
    entrypoint:
      - ./skitaid.py
      %s

  nginx:
    imasge: %s-nginx
    build:
      context: ../
      dockerfile: dep/Dockerfile.Nginx
    ports:
      - "80:80"
"""

DOCKER_COMPOSE_DEV = """
version: '2'
services:
  %s-dev:
    imasge: %s-dev
    container_name: %s-dev
    build:
      context: .
      dockerfile: Dockerfile
    user: ubuntu
    ports:
      - "%s:%s"
    volumes:
      - ${HOME}:${HOME}
    stdin_open: true
    tty: true
    entrypoint:
      - /bin/bash
"""

DOCKER_FILE_DEV = """
FROM hansroh/ubuntu:aws

EXPOSE %s
ENV PYTHONUNBUFFERED=0

COPY requirements.txt /requirements.txt
RUN pip3 install -Ur /requirements.txt && rm -f /requirements.txt

WORKDIR %s

CMD [ "/bin/bash" ]
"""

DOCKER_FILE = """
FROM hansroh/ubuntu:aws

EXPOSE %s
ENV PYTHONUNBUFFERED=0

COPY requirements.txt /requirements.txt
RUN pip3 install -Ur /requirements.txt && rm -f /requirements.txt
RUN pip3 install -U atila-vue

WORKDIR /home/ubuntu
COPY ./skitaid.py ./skitaid.py
COPY ./pwa ./pwa

CMD [ "/bin/bash" ]
"""

def generate (basedir, vhost, conf):
    nginxdir = os.path.join (basedir, 'nginx', 'conf.d')
    project_root = os.path.dirname (basedir)
    assert os.getenv ('STATIC_ROOT'), "missing STATIC_ROOT environment variable"
    assert conf ['name'], 'service name required, add skitai.run (name=NAME)'
    assert not os.path.exists (nginxdir), 'config path already exists, remove it'

    pathtool.mkdir (nginxdir)
    name = conf ['name']
    print ("configuring app {}".format (tc.info (name)))
    print ("bulding deployment docker files...")

    if not os.path.isfile (os.path.join (basedir, 'Dockerfile')):
        with open (os.path.join (basedir, 'Dockerfile'), 'w') as f:
            f.write (DOCKER_FILE % (conf.get ('port', 5000)))
    if not os.path.isfile (os.path.join (basedir, 'Dockerfile.Nginx')):
        with open (os.path.join (basedir, 'Dockerfile.Nginx'), 'w') as f:
            f.write (DOCKER_FILE_NGINX)
    if not os.path.isfile (os.path.join (basedir, 'docker-compose.yml')):
        with open (os.path.join (basedir, 'docker-compose.yml'), 'w') as f:
            f.write (DOCKER_COMPOSE % (
                name, name,
                conf.get ('port', 5000), conf.get ('port', 5000),
                "" if conf.get ('media_url') else '- --disable-static',
                name,
            ))

    print ("bulding development docker files...")
    if not os.path.isfile (os.path.join (project_root, 'Dockerfile')):
        with open (os.path.join (project_root, 'Dockerfile'), 'w') as f:
            f.write (DOCKER_FILE_DEV % (conf.get ('port', 5000), project_root))
    if not os.path.isfile (os.path.join (project_root, 'docker-compose.yml')):
        with open (os.path.join (project_root, 'docker-compose.yml'), 'w') as f:
            f.write (DOCKER_COMPOSE_DEV % (
                name, name, name,
                conf.get ('port', 5000), conf.get ('port', 5000)
            ))

    print ("bulding nginx configuration...")
    A, B, C = _collect_routes (vhost)
    pathtool.mkdir (os.path.join (nginxdir, 'include'))
    with open (os.path.join (nginxdir, 'default.conf'), 'w') as f:
        f.write (NGINX)

    print ("- setup document root...")
    root = os.getenv ('STATIC_ROOT')
    with open (os.path.join (nginxdir, 'include', 'header.conf'), 'w') as f:
        f.write (HEADER)

    print ("- setup upstreams...")
    upstreams = []
    with open (os.path.join (nginxdir, 'include', 'upstreams.conf'), 'w') as f:
        f.write (UPSTREAMS)
        f.write (UPSTREAM % ('backend', "    server {}:{};".format (name, conf.get ('port', 5000))))
        for path, rscs in sorted (B.items (), key = lambda x: len (x [0])):
            if not path:
                path = '/'
            for cname, rsc in rscs:
                servers = []
                for member, weight in rsc:
                    servers.append ("    server {} weight={};".format (member, weight))
            f.write (UPSTREAM % (cname, '\n'.join (servers)))
            upstreams.append ((path, cname))

    with open (os.path.join (nginxdir, 'include', 'routes.conf'), 'w') as f:
        for path, cname in upstreams:
            f.write (LOCATION_PROXY % (path, cname))

        f.write (LOCATIONS)

    print ("- collecting static files...")
    copied = 0
    for path, rscs in sorted (A.items (), key = lambda x: len (x [0]), reverse = True):
        if not path:
            path = '/'
        for rsc in rscs [::-1]:
            target = root + path
            pathtool.mkdir (target)
            r = copy_tree (rsc ['path'], target, update = 1, verbose = 1)
            copied += len (r)
    print ("- total {} static files collected".format (tc.warn ('{:,}'.format (copied))))
    print ("configurations are generate at {}.".format (tc.blue (basedir)))
