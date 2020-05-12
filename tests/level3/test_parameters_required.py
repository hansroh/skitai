import skitai
import confutil
import pprint
import re

def test_error_handler (app):
    @app.route ("/")
    @app.require ("URL", ["limit"])
    def index (was, limit):
        return ""

    @app.route ("/2")
    @app.require ("FORM", ["limit"])
    def index2 (was, limit):
        return ""

    @app.route ("/3")
    @app.require ("JSON", ["limit"])
    def index3 (was, limit):
        return ""

    @app.route ("/4")
    @app.require ("ARGS", ["limit"])
    def index4 (was, limit):
        return ""

    @app.route ("/5")
    @app.require ("ARGS", emails = ["email"], uuids = ["uuid"])
    def index5 (was, email = None, uuid = None):
        return ""

    @app.route ("/6")
    @app.require ("ARGS", a__gte = 5, b__between = (-4, -1), c__in = (1, 2))
    def index6 (was, **url):
        return ""

    @app.route ("/7")
    @app.require ("ARGS", a = re.compile ("^hans"), b__len__between = (4, 8))
    def index7 (was, a = None, b = None):
        return ""

    @app.route ("/8")
    @app.require ("DATA", ["limit"])
    def index8 (was, limit):
        return ""

    @app.route ("/9")
    @app.require ("DATA", lists = ['a'])
    def index9 (was, a):
        return ""

    @app.route ("/10")
    @app.require ("DATA", booleans = ['a'])
    def index10 (was, a):
        return ""

    @app.route ("/11")
    @app.require ("DATA", dicts = ['a'])
    def index11 (was, a):
        return ""

    @app.route ("/12")
    @app.require ("DATA", strings = ['a'])
    def index12 (was, a):
        return ""

    @app.route ("/13")
    @app.require (a = str, b = int)
    def index13 (was, a, b = None):
        return ""

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.status_code == 400

        resp = cli.get ("/?limit=4")
        assert resp.status_code == 200

        resp = cli.get ("/2?limit=4")
        assert resp.status_code == 200

        resp = cli.post ("/2", {"limit": 4})
        assert resp.status_code == 200

        resp = cli.post ("/2", {})
        assert resp.status_code == 400

        api = cli.api ()
        resp = api ("2").post ({"limit": 4})
        assert resp.status_code == 400

        api = cli.api ()
        resp = api ("3").post ({"limit": 4})
        assert resp.status_code == 200

        api = cli.api ()
        resp = api ("4").post ({"limit": 4})
        assert resp.status_code == 200

        resp = cli.get ("/4?limit=4")
        assert resp.status_code == 200

        resp = cli.post ("/4", {"limit": 4})
        assert resp.status_code == 200

        resp = cli.post ("/5", {"email": "hansroh@gmail.com"})
        assert resp.status_code == 200

        resp = cli.post ("/5", {"email": "hansroh@gmail"})
        assert resp.status_code == 400

        resp = cli.post ("/5", {"uuid": "123e4567-e89b-12d3-a456-426655440000"})
        assert resp.status_code == 200

        resp = cli.post ("/5", {"uuid": "123e4567-e89b-12d3-a456-42665544000"})
        assert resp.status_code == 400

        resp = cli.post ("/5", {"uuid": "123e4567-e89b-12d3-g456-426655440000"})
        assert resp.status_code == 400

        resp = cli.post ("/6", {"a": "5"})
        assert resp.status_code == 200

        resp = cli.post ("/6", {"a": "4"})
        assert resp.status_code == 400

        resp = cli.post ("/6", {"b": "-3"})
        assert resp.status_code == 200

        resp = cli.post ("/6", {"b": "4"})
        assert resp.status_code == 400

        resp = cli.post ("/6", {"c": "1"})
        assert resp.status_code == 200

        resp = cli.post ("/6", {"c": "3"})
        assert resp.status_code == 400

        resp = cli.post ("/7", {"a": "hansroh"})
        assert resp.status_code == 200

        resp = cli.post ("/7", {"a": "xxxx"})
        assert resp.status_code == 400

        resp = cli.post ("/7", {"b": "xxxx"})
        assert resp.status_code == 200

        resp = cli.post ("/7", {"b": "xxx"})
        assert resp.status_code == 400

        resp = cli.api()("7").post ({"b": "xxx"})
        assert resp.status_code == 400

        resp = cli.post ("/8", {"limit": 4})
        assert resp.status_code == 200

        resp = cli.api () ("8").post ({"limit": 4})
        assert resp.status_code == 200

        resp = cli.api () ("9").post ({"a": ''})
        assert resp.status_code == 200

        resp = cli.api () ("10").post ({"a": ''})
        assert resp.status_code == 400

        resp = cli.api () ("10").post ({"a": 'xx'})
        assert resp.status_code == 400

        resp = cli.api () ("10").post ({"a": 'yes'})
        assert resp.status_code == 200

        resp = cli.api () ("10").post ({"a": 'true'})
        assert resp.status_code == 200

        resp = cli.api () ("10").post ({"a": 'no'})
        assert resp.status_code == 200

        resp = cli.api () ("10").post ({"a": 'false'})
        assert resp.status_code == 200

        resp = cli.api () ("11").post ({"a": {"a": 1}})
        assert resp.status_code == 200

        resp = cli.api () ("11").post ({"a": [1,2]})
        assert resp.status_code == 400

        resp = cli.api () ("11").post ({"a": ''})
        assert resp.status_code == 400

        resp = cli.api () ("12").post ({"a": ''})
        assert resp.status_code == 200

        resp = cli.api () ("12").post ({"a": 0})
        assert resp.status_code == 400

        resp = cli.api () ("12").post ({"a": {}})
        assert resp.status_code == 400

        resp = cli.api () ("13").post ({"a": 1})
        assert resp.status_code == 400

        resp = cli.api () ("13").post ({"a": '1'})
        assert resp.status_code == 200

        resp = cli.api () ("13").post ({"a": None})
        assert resp.status_code == 200

        resp = cli.api () ("13").post ({"a": None, "b": 1})
        assert resp.status_code == 200



def test_error_handler_2 (app):
    @app.route ("/20")
    @app.require ("GET", ["limit"], ints = ['limit'])
    @app.require ("POST", ["id"])
    def index20 (was, limit = 10, **DATA):
        if was.request.method == "POST":
            assert DATA ['id']
        return 'OK'

    @app.route ("/21")
    @app.require ("URL", ["limit"], ints = ['limit'])
    @app.require ("POST", ["id"])
    def index21 (was, limit, **DATA):
        if was.request.method == "POST":
            assert DATA ['id']
        return 'OK'

    @app.route ("/22")
    @app.require ("POST", ["id"])
    def index21 (was, limit, **DATA):
        if was.request.method == "POST":
            assert DATA ['id']
        return 'OK'

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/20")
        assert resp.status_code == 400

        resp = cli.get ("/20?limit=4")
        assert resp.status_code == 200

        resp = cli.post ("/20?limit=4", {})
        assert resp.status_code == 400

        resp = cli.post ("/20?limit=4", {'id': 'ttt'})
        assert resp.status_code == 200

        resp = cli.post ("/20", {'id': 'ttt'})
        assert resp.status_code == 200

        resp = cli.get ("/21")
        assert resp.status_code == 400

        resp = cli.get ("/21?limit=4")
        assert resp.status_code == 200

        resp = cli.post ("/21?limit=4", {})
        assert resp.status_code == 400

        resp = cli.post ("/21", {'id': 'ttt'})
        assert resp.status_code == 400

        resp = cli.get ("/22")
        assert resp.status_code == 400