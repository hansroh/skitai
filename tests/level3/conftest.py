import pytest
from functools import partial
import skitai
import platform
import sys
import os

def add_cluster (wasc, name, args):
    ctype, members, policy, ssl, max_conns = args
    wasc.add_cluster (ctype, name, members, ssl, policy, max_conns or 10)

@pytest.fixture
def service_layer (wasc):
    if os.path.exists ('/tmp/.temp.db3'):
        os.remove ('/tmp/.temp.db3')
    sys.path.append ('level3/models')
    os.environ.setdefault ('DJANGO_SETTINGS_MODULE', 'config.settings')
    os.environ ['DBENGINE'] = 'sqlite3://{}'.format ('/tmp/.temp.db3')
    os.environ ['SECRET_KEY'] = 'OVERWRITE WITH YOUR SECRET KEY'
    import django; django.setup ()
    from django.conf import settings
    from django.core import management
    management.call_command ("migrate", no_input=True)
    add_cluster (wasc, *skitai.alias ("@rdb", skitai.DB_SQLITE3, '/tmp/.temp.db3'))
    yield settings
    os.remove ('/tmp/.temp.db3')
