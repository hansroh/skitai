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

def test_error_handler_2 (app):
    @app.route ("/")
    @app.require ("GET", ["limit"], ints = ['limit'])
    @app.require ("POST", ["id"])
    def index20 (was, limit, **DATA):
        if was.request.method == "POST":
            assert DATA ['id']
        return 'OK'

    with app.test_client ("/", confutil.getroot ()) as cli:       
        resp = cli.get ("/")
        assert resp.status_code == 400
        
        resp = cli.get ("/?limit=4")
        assert resp.status_code == 200  

        resp = cli.post ("/?limit=4", {})
        assert resp.status_code == 400        

        resp = cli.post ("/?limit=4", {'id': 'ttt'})
        assert resp.status_code == 200    
        
        