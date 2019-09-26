import skitai
import confutil
import pprint
from skitai import was as the_was

def test_futures (app, dbpath):
    @app.route ("/")
    def index (was):
        def respond (was, rss):
            return the_was.response.API (status_code = [rs.status_code for rs in rss.dispatch ()], a = rss.a)

        reqs = [
            the_was.get ("@pypi/project/skitai/"),
            the_was.get ("@pypi/project/rs4/"),
            the_was.backend ("@sqlite").execute ('SELECT * FROM stocks WHERE symbol=?', ('RHAT',))
        ]
        return the_was.Tasks (reqs, a = 100).then (respond)

    @app.route ("/3")
    def index3 (was):
        def respond (was, rss):
            datas = str (rss [0].fetch ()) + str (rss [1].one ())
            return datas

        reqs = [
            the_was.get ("@pypi/project/rs4/"),
            the_was.backend ("@sqlite").execute ('SELECT * FROM stocks WHERE symbol=?', ('RHAT',))
        ]
        return the_was.Tasks (reqs).then (respond)

    @app.route ("/4")
    def index4 (was):
        def respond (was, rss):
            return str (rss [0].one ())

        reqs = [
            the_was.backend ("@sqlite").execute ('SELECT * FROM stocks WHERE symbol=?', ('---',))
        ]
        return the_was.Tasks (reqs).then (respond)

    @app.route ("/12")
    def index12 (was):
        a = the_was.Tasks ([was.backend ("@sqlite").execute ('SELECT symbol FROM stocks WHERE symbol=? limit 1', ('RHAT',))])
        b = the_was.Tasks ([was.backend ("@sqlite").execute ('SELECT symbol FROM stocks WHERE symbol=? limit 1', ('RHAT',))])
        a.add (b)
        return str (a.one ())

    @app.route ("/13")
    def index13 (was):
        def respond (was, rss):
            return str (rss.one ())
        a = was.Tasks ([the_was.backend ("@sqlite").execute ('SELECT symbol FROM stocks WHERE symbol=? limit 1', ('RHAT',))])
        b = was.Tasks ([the_was.backend ("@sqlite").execute ('SELECT symbol FROM stocks WHERE symbol=? limit 1', ('RHAT',))])
        a.merge (b)
        return a.then (respond)

    app.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")
    app.alias ("@sqlite", skitai.DB_SQLITE3, dbpath)
    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.data ['status_code'] == [200, 200, 200]
        assert resp.data ['a'] == 100

        resp = cli.get ("/3")
        assert "hansroh" in resp.text
        assert "RHAT" in resp.text

        resp = cli.get ("/4")
        assert resp.status_code == 410

        resp = cli.get ("/12")
        assert resp.data == "[{'symbol': 'RHAT'}, [{'symbol': 'RHAT'}]]"

        resp = cli.get ("/13")
        assert resp.data == "[{'symbol': 'RHAT'}, {'symbol': 'RHAT'}]"
