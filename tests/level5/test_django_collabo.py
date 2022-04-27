import requests
import os
import shutil

def test_django_collabo (launch):
    os.mkdir (".temp")
    os.chdir (".temp")
    try:
        r = requests.get ("https://gitlab.com/skitai/atila/-/raw/master/atila/collabo/django/manage.py")
        with open ("manage.py", "w") as f:
            f.write (r.text)
        assert r.status_code == 200
        assert os.path.isfile ("manage.py")
        os.system ("chmod +x manage.py")
        os.system ("./manage.py startproject")
        assert os.path.isfile ("skitaid.py")
        os.system ("./manage.py migrate")
        assert os.path.isfile ("pwa/models/db.sqlite3")
        os.system ("./manage.py collectstatic")
        assert os.path.isdir ("pwa/models/static/admin")

        with launch ("./skitaid.py") as engine:
            r = engine.get ("/admin")
            assert r.status_code == 200

            r = engine.get ("/")
            assert r.status_code == 404

    finally:
        os.chdir ("..")
        shutil.rmtree (".temp")
