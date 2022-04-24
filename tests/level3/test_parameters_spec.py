import skitai
import confutil
import pprint
import re

def test_spec1 (app):
    @app.route ("/")
    @app.spec ("URL", ["limit"])
    def index (was, limit):
        return ""

    @app.route ("/2")
    @app.spec ("FORM", ["limit"])
    def index2 (was, limit):
        return ""

    @app.route ("/3")
    @app.spec ("JSON", ["limit"])
    def index3 (was, limit):
        return ""

    @app.route ("/4")
    @app.spec ("ARGS", ["limit"])
    def index4 (was, limit):
        return ""

    @app.route ("/5")
    @app.spec ("ARGS", emails = ["email"], uuids = ["uuid"])
    def index5 (was, email = None, uuid = None):
        return ""

    @app.route ("/6")
    @app.spec ("ARGS", a__gte = 5, b__between = (-4, -1), c__in = (1, 2))
    def index6 (was, **url):
        return ""

    @app.route ("/7")
    @app.spec ("ARGS", a = re.compile ("^hans"), b__len__between = (4, 8))
    def index7 (was, a = None, b = None):
        return ""

    @app.route ("/8")
    @app.spec ("DATA", ["limit"])
    def index8 (was, limit):
        return ""

    @app.route ("/9")
    @app.spec ("DATA", lists = ['a'])
    def index9 (was, a):
        return ""

    @app.route ("/10")
    @app.spec ("DATA", bools = ['a'])
    def index10 (was, a):
        return ""

    @app.route ("/11")
    @app.spec ("DATA", dicts = ['a'])
    def index11 (was, a):
        return ""

    @app.route ("/12")
    @app.spec ("DATA", strings = ['a'])
    def index12 (was, a):
        return ""

    @app.route ("/13")
    @app.spec (a = str, b = [int, float])
    def index13 (was, a, b = None):
        return ""

    @app.route ("/14")
    @app.spec (a__startswith = 'a_', b__notstartwith = 'a_', c__endswith = '_z', d__notendwith = '_z', e__contains = '_x' , f__notcontain = '_x')
    def index14 (was, a, b, c, d, e, f):
        return ""

    @app.route ("/15")
    @app.spec (d___k__1__gte = 10)
    def index15 (was, d):
        return ""

    @app.route ("/16")
    @app.spec (d___k__1__len__gte = 3)
    def index16 (was, d):
        return ""

    @app.route ("/17")
    @app.spec (d___k__len__gte = 3)
    def index17 (was, d):
        return ""

    def verify (was, d):
        if d == True:
            return 777
        raise was.Error ("444 Bad Request")

    @app.route ("/18")
    @app.spec (d = verify)
    def index18 (was, d):
        return was.API (r = d)

    @app.route ("/19")
    @app.spec (d = int)
    def index19 (was, d):
        return was.API (r = d)

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

        resp = cli.api () ("13").post ({"a": None, "b": 1.0})
        assert resp.status_code == 200

        d = dict (
            a = 'a_1',
            b = 'b_1',
            c = '1_z',
            d = '1_y',
            e = '1_x_1',
            f = '1_y_1',
        )
        resp = cli.api () ("14").post (d)
        assert resp.status_code == 200

        d1 = d.copy (); d1 ['b'] = 'a_2'
        resp = cli.api () ("14").post (d1)
        assert resp.status_code == 400

        d1 = d.copy (); d1 ['d'] = '2_z'
        resp = cli.api () ("14").post (d1)
        assert resp.status_code == 400

        d1 = d.copy (); d1 ['f'] = '2_x_2'
        resp = cli.api () ("14").post (d1)
        assert resp.status_code == 400

        d1 = d.copy (); d1 ['a'] = 'b_2'
        resp = cli.api () ("14").post (d1)
        assert resp.status_code == 400

        d1 = d.copy (); d1 ['c'] = '2_y'
        resp = cli.api () ("14").post (d1)
        assert resp.status_code == 400

        d1 = d.copy (); d1 ['e'] = '2_y_2'
        resp = cli.api () ("14").post (d1)
        assert resp.status_code == 400

        resp = cli.api () ("15").post ({"d": {"k": [5, 11]}})
        assert resp.status_code == 200

        resp = cli.api () ("15").post ({"d": {"k": [5, 9]}})
        assert resp.status_code == 400

        resp = cli.api () ("16").post ({"d": {"k": ['aa', 'aaaa']}})
        assert resp.status_code == 200

        resp = cli.api () ("16").post ({"d": {"k": ['aa', 'a']}})
        assert resp.status_code == 400

        resp = cli.api () ("17").post ({"d": {"k": 'aaaa'}})
        assert resp.status_code == 200

        resp = cli.api () ("17").post ({"d": {"k": 'a'}})
        assert resp.status_code == 400

        resp = cli.api () ("18").post ({"d": True})
        assert resp.status_code == 200
        assert resp.data ['r'] == 777

        resp = cli.api () ("18").post ({"d": False})
        assert resp.status_code == 444

        resp = cli.get ("19?d=777")
        assert resp.status_code == 200
        assert resp.data ['r'] == 777


def test_spec2 (app):
    @app.route ("/20", methods = ["GET", "POST"])
    def index20 (was, d, k = 1):
        return was.API (r = d)

    @app.route ("/21", methods = ["GET", "POST"])
    @app.spec (url = ["d"])
    def index21 (was, d, k = 1):
        return was.API (r = d)

    @app.route ("/22", methods = ["GET", "POST"])
    @app.spec ()
    def index22 (was, d, k = 1):
        return was.API (r = d)

    def check (was):
        assert isinstance (was.request.ARGS ["limit"], int)

    @app.route ("/23")
    @app.spec (url = ["id", "limit"], limit = int)
    @app.depends (check)
    def index23 (was, id, limit, **DATA):
        return 'OK'

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("20?d=777")
        assert resp.status_code == 200

        resp = cli.post ("20?d=777", {"k": 3})
        assert resp.status_code == 200

        resp = cli.post ("22?d=777", {"k": 3})
        assert resp.status_code == 400

        resp = cli.post ("20", {"d": 777})
        assert resp.status_code == 200

        resp = cli.post ("21?k=1", {"d": 777})
        assert resp.status_code == 400

        resp = cli.post ("21", {"d": 777, "k": 2})
        assert resp.status_code == 200

        resp = cli.post ("22", {"d": 777, "k": 2})
        assert resp.status_code == 200

        resp = cli.post ("22?d=777", {"k": 2})
        assert resp.status_code == 400

        resp = cli.post ("22?d=777", {"k": 2})
        assert resp.status_code == 400

        resp = cli.get ("23?id=777&limit=10")
        assert resp.status_code == 200

        resp = cli.get ("23?id=777&limit=10&x=4")
        assert resp.status_code == 400

        resp = cli.post ("23?id=777&limit=10&x=4", {})
        assert resp.status_code == 400

        resp = cli.post ("23?id=777&limit=10", dict (x = 4))
        assert resp.status_code == 200

        resp = cli.post ("23?id=777", dict (x = 4, limit = 10))
        assert resp.status_code == 400
