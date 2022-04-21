import skitai
import confutil
import pprint

def test_futures (app, dbpath):
    @app.route ("/")
    def index (was):
        def respond (was, rss):
            return skitai.was.response.API (status_code = [rs.status_code for rs in rss.dispatch ()], a = rss.meta ['a'])

        reqs = [
            skitai.was.Mask ("@pypi/project/skitai/"),
            skitai.was.Mask ("@pypi/project/rs4/"),
            skitai.was.Mask ("@sqlite")
        ]
        return skitai.was.Tasks (reqs, meta = {'a': 100}).then (respond)

    @app.route ("/3")
    def index3 (was):
        def respond (was, rss):
            datas = str (rss [0].fetch ()) + str (rss [1].one ())
            return datas

        reqs = [
            skitai.was.Mask ("@pypi/project/rs4/"),
            skitai.was.Mask (['RHAT'])
        ]
        return skitai.was.Tasks (reqs).then (respond)

    @app.route ("/4")
    def index4 (was):
        def respond (was, rss):
            return str (rss [0].one ())

        reqs = [
            skitai.was.Mask ([])
        ]
        return skitai.was.Tasks (reqs).then (respond)

    @app.route ("/12")
    def index12 (was):
        a = skitai.was.Tasks ([was.Mask ([{'symbol': 'RHAT'}])])
        b = skitai.was.Tasks ([was.Mask ([{'symbol': 'RHAT'}])])
        a.add (b)
        return str (a.one ())

    @app.route ("/13")
    def index13 (was):
        def respond (was, rss):
            return str (rss.one ())
        a = skitai.was.Tasks ([was.Mask ([{'symbol': 'RHAT'}])])
        b = skitai.was.Tasks ([was.Mask ([{'symbol': 'RHAT'}])])
        a.merge (b)
        return a.then (respond)

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.data ['status_code'] == [200, 200, 200]
        assert resp.data ['a'] == 100

        resp = cli.get ("/3")
        assert "@pypi" in resp.text
        assert "RHAT" in resp.text

        resp = cli.get ("/4")
        assert resp.status_code == 410

        resp = cli.get ("/12")
        assert resp.data == "[{'symbol': 'RHAT'}, [{'symbol': 'RHAT'}]]"

        resp = cli.get ("/13")
        assert resp.data == "[{'symbol': 'RHAT'}, {'symbol': 'RHAT'}]"
