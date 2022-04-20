import atila
import skitai
import confutil
import pprint

def func1 ():
    return 'thread'

def func2 ():
    return 'process'

def test_futures (app, dbpath):
    # IMP: becasue of executor shutdown, run test first
    @app.route ("/")
    def index (was):
        def respond (was, rss):
            return was.response.API (status_code = [rs.status_code for rs in rss.dispatch ()], a = rss.meta ["a"])

        reqs = [
            was.Mask ("@pypi/project/skitai/"),
            was.Mask ("@pypi/project/rs4/"),
            was.Mask ([{'symbol': 'RHAT'}, {'symbol': 'RHAT'}])
        ]
        return was.Tasks (reqs, meta = {'a': 100}).then (respond)

    @app.route ("/1")
    def index1 (was):
        def respond (was, task):
            return was.response.API (status_code = task.dispatch ().status_code, a = task.meta ["a"])
        return was.Mask ("@pypi/project/skitai/", meta = {'a': 100}).then (respond)

    @app.route ("/1-1")
    def index1_1 (was):
        def respond2 (was, task):
            return was.API (status_code = task.dispatch ().status_code)
        def respond (was, task):
            return was.Mask ("@pypi/project/rs4/").then (respond2)
        return was.Mask ("@pypi/project/skitai/").then (respond)

    @app.route ("/2")
    def index2 (was):
        def repond (was, rss):
            return was.response.API (status_code_db = [rs.status_code for rs in rss.dispatch ()], b = rss.meta ['b'], status_code = rss.meta ['status_code'])

        def checkdb (was, rss):
            reqs = [was.Mask ([{'symbol': 'RHAT'}, {'symbol': 'RHAT'}])]
            rss.meta ['b'] = rss.meta ["a"] + 100
            rss.meta ['status_code'] = [rs.status_code for rs in rss.dispatch ()]
            return was.Tasks (reqs, meta = rss.meta).then (repond)

        def begin ():
            reqs = [
                was.Mask ("@pypi/project/skitai/"),
                was.Mask ("@pypi/project/rs4/")
            ]
            return was.Tasks (reqs, meta = {'a': 100}).then (checkdb)
        begin ()

    @app.route ("/3")
    def index3 (was):
        def respond (was, rss):
            datas = str (rss [0].fetch ()) + str (rss [1].one ())
            return datas

        reqs = [
            was.Mask ("@pypi/project/rs4/"),
            was.Mask ([{'symbol': 'RHAT'}])
        ]
        return was.Tasks (reqs).then (respond)

    @app.route ("/4")
    def index4 (was):
        def respond (was, rss):
            return str (rss [0].one ())

        reqs = [was.Mask ([])]
        return was.Tasks (reqs).then (respond)

    @app.route ("/4-1")
    def index4_1 (was):
        def respond (was, rs):
            return str (rs.fetch ())
        req = was.Mask ([])
        return req.then (respond)

    @app.route ("/5")
    def index5 (was):
        reqs = [
            was.Mask ("@pypi/project/rs4/"),
            was.Mask ([{'symbol': 'RHAT'}, {'symbol': 'RHAT'}])
        ]
        return str ([rs.fetch () for rs in was.Tasks (reqs)])

    @app.route ("/6")
    def index6 (was):
        reqs = [
            was.Mask ("@pypi/project/rs4/"),
            was.Mask ([{'symbol': 'RHAT'}, {'symbol': 'RHAT'}])
        ]
        return str (was.Tasks (reqs).fetch ())

    @app.route ("/7")
    def index7 (was):
        reqs = [
            was.Mask ([{'symbol': 'RHAT'}]),
            was.Mask ([{'symbol': 'RHAT'}])
        ]
        return str (was.Tasks (reqs).one ())

    @app.route ("/8")
    def index8 (was):
        reqs = [
            was.Mask ([]),
            was.Mask ([{'symbol': 'RHAT'}])
        ]
        return str (was.Tasks (reqs).one ())

    @app.route ("/11")
    def index11 (was):
        reqs = [
            was.Mask ([]),
            was.Mask ([{'symbol': 'RHAT'}])
        ]
        return str (was.Tasks (reqs).one ())

    @app.route ("/12")
    def index12 (was):
        a = was.Tasks ([was.Mask ([{'symbol': 'RHAT'}])])
        b = was.Tasks ([was.Mask ([{'symbol': 'RHAT'}])])
        a.add (b)
        return str (a.one ())

    @app.route ("/13")
    def index13 (was):
        def respond (was, rss):
            return str (rss.one ())
        a = was.Tasks ([was.Mask ([{'symbol': 'RHAT'}])])
        b = was.Tasks ([was.Mask ([{'symbol': 'RHAT'}])])
        a.merge (b)
        return a.then (respond)

    @app.route ("/14")
    def index14 (was):
        reqs = [
            was.Mask ([]),
            was.Mask ([{'symbol': 'RHAT'}])
        ]
        tasks = was.Tasks (reqs)
        req = was.Mask ([{'symbol': 'RHAT'}])
        (a, b), c = was.Tasks ([tasks, req]).fetch ()
        return str ([a,b,c])

    @app.route ("/15")
    def index15 (was):
        reqs = [
            was.Mask ([]),
            was.Mask ([{'symbol': 'RHAT'}])
        ]
        tasks = was.Tasks (reqs)
        req = was.Mask ([{'symbol': 'RHAT'}])
        mask = was.Mask (['mask'])
        (a, b), c, d = was.Tasks ([tasks, req, mask]).fetch ()
        return str ([a, b, c, d])

    @app.route ("/16")
    def index16 (was):
        reqs = [
            was.Mask ([]),
            was.Mask ([{'symbol': 'RHAT'}])
        ]
        tasks = was.Tasks (reqs)
        req = was.Mask ([{'symbol': 'RHAT'}])
        mask = was.Mask (['mask'])
        th = was.Thread (func1)
        ps = was.Process (func2)
        (a, b), c, d, e, f = was.Tasks ([tasks, req, mask, th, ps]).fetch ()
        return str ([a, b, c, d, e, f])

    @app.route ("/17")
    def index17 (was):
        reqs = [
            was.Mask ([]),
            was.Thread (func1) or was.Mask ('thread')
        ]
        reqs = [
            was.Tasks (reqs),
            was.Mask (['mask']),
            was.Thread (func1),
            was.Process (func2)
        ]
        tasks = was.Tasks (reqs)
        req = was.Mask ([{'symbol': 'RHAT'}])
        mask = was.Mask (['mask'])

        ((a, b), c, d, e), e, f = was.Tasks ([tasks, req, mask]).fetch ()
        return str ([a, b, c, d, e, f])

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/")
        assert resp.data ['status_code'] == [200, 200, 200]
        assert resp.data ['a'] == 100

        resp = cli.get ("/1")
        assert resp.data ['status_code'] == 200
        assert resp.data ['a'] == 100

        resp = cli.get ("/1-1")
        assert resp.data ['status_code'] == 200

        resp = cli.get ("/2")
        assert resp.data ['status_code'] == [200, 200]
        assert resp.data ['status_code_db'] == [200]
        assert resp.data ['b'] == 200

        resp = cli.get ("/3")
        assert "@pypi" in resp.text
        assert "RHAT" in resp.text

        resp = cli.get ("/4")
        assert resp.status_code == 410

        resp = cli.get ("/4-1")
        assert resp.status_code == 200
        assert resp.data == '[]'

        resp = cli.get ("/5")
        assert "@pypi" in resp.text
        assert "RHAT" in resp.text

        resp = cli.get ("/6")
        assert "@pypi" in resp.text
        assert "RHAT" in resp.text

        resp = cli.get ("/7")
        assert "RHAT" in resp.text

        resp = cli.get ("/8")
        assert resp.status_code == 410

        resp = cli.get ("/11")
        assert resp.status_code == 410

        resp = cli.get ("/12")
        assert resp.data == "[{'symbol': 'RHAT'}, [{'symbol': 'RHAT'}]]"

        resp = cli.get ("/13")
        assert resp.data == "[{'symbol': 'RHAT'}, {'symbol': 'RHAT'}]"

        resp = cli.get ("/14")
        assert resp.data == "[[], [{'symbol': 'RHAT'}], [{'symbol': 'RHAT'}]]"

        resp = cli.get ("/15")
        assert resp.data == "[[], [{'symbol': 'RHAT'}], [{'symbol': 'RHAT'}], ['mask']]"

        resp = cli.get ("/16")
        assert resp.data == "[[], [{'symbol': 'RHAT'}], [{'symbol': 'RHAT'}], ['mask'], 'thread', 'process']"

        resp = cli.get ("/17")
        assert resp.data == "[[], 'thread', ['mask'], 'thread', [{'symbol': 'RHAT'}], ['mask']]"
