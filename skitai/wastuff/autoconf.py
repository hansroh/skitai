
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

DOCKER_FILE_NGINX = """FROM nginx

COPY ./dep/nginx/conf.d /etc/nginx/conf.d
COPY ./dep/nginx/.static_root /var/www/html
"""

DOCKER_COMPOSE = """version: '2'

services:
  {name}:
    image: {name}
    build:
      context: ..
      dockerfile: dep/production.Dockerfile
    user: ubuntu
    ports:
      - "{port}:{port}"
    volumes:
      - {media_path}:{media_path}
    tty: true
    entrypoint:
      - /bin/bash
      - ./dep/startup.sh

  nginx:
    image: {name}-nginx
    build:
      context: ..
      dockerfile: dep/production.nginx.Dockerfile
    ports:
      - "80:80"
    volumes:
      - {media_path}:/var/www/pub
"""

DOCKER_COMPOSE_DEV = """version: '2'
services:
  {name}-dev:
    image: {name}-dev
    container_name: {name}-dev
    build:
      context: ..
      dockerfile: devel.Dockerfile
    user: ubuntu
    ports:
      - "{port}:{port}"[]
    volumes:
      - ${{PWD}}:${{HOME}}/app
      - ${{HOME}}/.ssh:/home/ubuntu/.ssh
    tty: true
    entrypoint:
      - /bin/bash
      - ./dep/devel.sh
"""

DOCKER_FILE_DEV = """FROM hansroh/ubuntu:aws

ENV PYTHONUNBUFFERED=0
COPY requirements.txt /requirements.txt
RUN pip3 install -Ur /requirements.txt && rm -f /requirements.txt

WORKDIR /home/ubuntu/app
EXPOSE {port}
"""

DOCKER_FILE = """FROM hansroh/ubuntu:aws

ENV PYTHONUNBUFFERED=0

WORKDIR /home/ubuntu/app
COPY requirements.txt /requirements.txt
RUN pip3 install -Ur /requirements.txt && rm -f /requirements.txt
RUN pip3 install -U atila-vue

COPY ./dep ./dep
COPY ./pwa ./pwa
COPY ./skitaid.py ./skitaid.py

EXPOSE {port}
"""

DEVEL = """#! /bin/bash
./skitaid.py --devel
"""

PRODUCTION = """#! /bin/bash
sudo chown -R ubuntu:ubuntu /home/ubuntu
./skitaid.py --disable-static
"""

STARTUP = """#! /bin/bash

req=$(which "docker-compose")
if [ "$req" == "" ]
then
    echo "installing docker-compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/1.28.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    sudo rm -f /usr/bin/docker-compose && sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
fi

SERVICE="stt-api-dev"
if [ "$1" == "bash" ]""
then
    docker exec -it $SERVICE /bin/bash
elif [ "$1" == "test" ]
then
    docker exec -it $SERVICE /bin/bash -c "cd tests && ./test-all.sh"
elif [ "$1" == "exec" ]
then
    docker exec -it $SERVICE $2 $3 $4 $5 $6 $7 $8 $9
else
    docker-compose -f dep/devel.yml $1 $2 $3 $4 $5 $6 $7 $8 $9
fi
"""

def generate (project_root, vhost, conf):
    depdir = os.path.join (project_root, 'dep')
    assert os.getenv ('STATIC_ROOT'), "missing STATIC_ROOT environment variable"
    assert conf ['name'], 'service name required, add skitai.run (name=NAME)'

    name = conf ['name']
    if not conf.get ('media_path'):
        conf ['media_url'] = None
        conf ['media_path'] = f'/home/ubuntu/.skitai/{name}/pub'
    conf ['media_volume_path'] = os.path.join (f'/home/ubuntu/.skitai')
    conf ['port'] = conf.get ('port', 5000)

    print ("configuring app {}".format (tc.info (name)))
    print ("generating deployment docker files...")
    pathtool.mkdir (depdir)
    if not os.path.isfile (os.path.join (depdir, 'production.Dockerfile')):
        print ("- production.Dockerfile")
        with open (os.path.join (depdir, 'production.Dockerfile'), 'w') as f:
            f.write (DOCKER_FILE.format (**conf))
    if not os.path.isfile (os.path.join (depdir, 'production.nginx.Dockerfile')):
        print ("- production.nginx.Dockerfile")
        with open (os.path.join (depdir, 'production.nginx.Dockerfile'), 'w') as f:
            f.write (DOCKER_FILE_NGINX)

    if not os.path.isfile (os.path.join (depdir, 'production.yml')):
        print ("- production.yml")
        with open (os.path.join (depdir, 'production.yml'), 'w') as f:
            f.write (DOCKER_COMPOSE.format (**conf))

    print ("generating development docker files...")
    if not os.path.isfile (os.path.join (depdir, 'devel.Dockerfile')):
        print ("- devel.Dockerfile")
        with open (os.path.join (depdir, 'devel.Dockerfile'), 'w') as f:
            f.write (DOCKER_FILE_DEV.format (**conf))
    if not os.path.isfile (os.path.join (depdir, 'devel.yml')):
        print ("- devel.yml")
        with open (os.path.join (depdir, 'devel.yml'), 'w') as f:
            f.write (DOCKER_COMPOSE_DEV.format (**conf))

    print ("generating shell scripts...")
    for fn, content in (('production.sh', PRODUCTION), ('devel.sh', DEVEL)):
        script = os.path.join (depdir, fn)
        if not os.path.isfile (script):
            print (f"- {fn}")
            with open (script, 'w') as f:
                f.write (content)
        os.chmod (script, 0o744)

    script = os.path.join (project_root, 'container.sh')
    if not os.path.isfile (script):
        print ("- container.sh")
        with open (script, 'w') as f:
            f.write (STARTUP.format (**conf))
    os.chmod (script, 0o744)

    print ("collecting routes to serve with Nginx...")
    A, B, C = _collect_routes (vhost)
    root = os.getenv ('STATIC_ROOT')
    nginxdir = os.path.join (depdir, 'nginx', 'conf.d')
    if not os.path.exists (nginxdir):
        pathtool.mkdir (nginxdir)
        print ("generating nginx configuration...")
        print ("- nginx/conf.d/default.conf")
        pathtool.mkdir (os.path.join (nginxdir, 'include'))
        with open (os.path.join (nginxdir, 'default.conf'), 'w') as f:
            f.write (NGINX)

        print ("- nginx/conf.d/include/header.conf")
        with open (os.path.join (nginxdir, 'include', 'header.conf'), 'w') as f:
            print ('  - / mounted to /var/www/html')
            f.write (HEADER)

        print ("- setup upstreams...")
        print ("- nginx/conf.d/include/upstream.conf")
        upstreams = []
        with open (os.path.join (nginxdir, 'include', 'upstreams.conf'), 'w') as f:
            f.write (UPSTREAMS)
            f.write (UPSTREAM % ('backend', "    server {}:{};".format (name, conf.get ('port', 5000))))
            for path, rscs in sorted (B.items (), key = lambda x: len (x [0])):
                if not path:
                    path = '/'
                for cname, rsc in rscs:
                    print (f'  - {cname} {rsc}')
                    servers = []
                    for member, weight in rsc:
                        servers.append ("    server {} weight={};".format (member, weight))
                f.write (UPSTREAM % (cname, '\n'.join (servers)))
                upstreams.append ((path, cname))

        print ("- setup routes...")
        print ("- nginx/conf.d/include/routes.conf")
        with open (os.path.join (nginxdir, 'include', 'routes.conf'), 'w') as f:
            for path, cname in upstreams:
                print (f'  - {path} mounted to {cname}')
                f.write (LOCATION_PROXY % (path, cname))
            if conf.get ("media_url"):
                print ('  - /var/www/pub mounted to {media_url}'.format (**conf))
                f.write ("location %s {\n    alias /var/www/pub;\n}\n" % conf ["media_url"][:-1])
            f.write (LOCATIONS)

    print ("collecting static files...")
    copied = 0
    for path, rscs in sorted (A.items (), key = lambda x: len (x [0]), reverse = True):
        if not path:
            path = '/'
        for rsc in rscs [::-1]:
            target = root + path
            pathtool.mkdir (target)
            r = copy_tree (rsc ['path'], target, update = 1, verbose = 1)
            print (f"- copying static: {rsc ['path'].replace ('/home/ubuntu', '~')}")
            copied += len (r)
    print ("total {} static files collected".format (tc.warn ('{:,}'.format (copied))))

    print ("configurations generated at {}.".format (tc.blue (depdir)))
