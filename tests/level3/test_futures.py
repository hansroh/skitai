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
    def index (context):
        def respond (context, rss):
            return context.response.API (status_code = [rs.status_code for rs in rss.dispatch ()], a = rss.meta ["a"])

        reqs = [
            context.Mask ("@pypi/project/skitai/"),
            context.Mask ("@pypi/project/rs4/"),
            context.Mask ([{'symbol': 'RHAT'}, {'symbol': 'RHAT'}])
        ]
        return context.Tasks (reqs, meta = {'a': 100}).then (respond)

    @app.route ("/1")
    def index1 (context):
        def respond (context, task):
            return context.response.API (status_code = task.dispatch ().status_code, a = task.meta ["a"])
        return context.Mask ("@pypi/project/skitai/", meta = {'a': 100}).then (respond)

    @app.route ("/1-1")
    def index1_1 (context):
        def respond2 (context, task):
            return context.API (status_code = task.dispatch ().status_code)
        def respond (context, task):
            return context.Mask ("@pypi/project/rs4/").then (respond2)
        return context.Mask ("@pypi/project/skitai/").then (respond)

    @app.route ("/2")
    def index2 (context):
        def repond (context, rss):
            return context.response.API (status_code_db = [rs.status_code for rs in rss.dispatch ()], b = rss.meta ['b'], status_code = rss.meta ['status_code'])

        def checkdb (context, rss):
            reqs = [context.Mask ([{'symbol': 'RHAT'}, {'symbol': 'RHAT'}])]
            rss.meta ['b'] = rss.meta ["a"] + 100
            rss.meta ['status_code'] = [rs.status_code for rs in rss.dispatch ()]
            return context.Tasks (reqs, meta = rss.meta).then (repond)

        def begin ():
            reqs = [
                context.Mask ("@pypi/project/skitai/"),
                context.Mask ("@pypi/project/rs4/")
            ]
            return context.Tasks (reqs, meta = {'a': 100}).then (checkdb)
        begin ()

    @app.route ("/3")
    def index3 (context):
        def respond (context, rss):
            datas = str (rss [0].fetch ()) + str (rss [1].one ())
            return datas

        reqs = [
            context.Mask ("@pypi/project/rs4/"),
            context.Mask ([{'symbol': 'RHAT'}])
        ]
        return context.Tasks (reqs).then (respond)

    @app.route ("/4")
    def index4 (context):
        def respond (context, rss):
            return str (rss [0].one ())

        reqs = [context.Mask ([])]
        return context.Tasks (reqs).then (respond)

    @app.route ("/4-1")
    def index4_1 (context):
        def respond (context, rs):
            return str (rs.fetch ())
        req = context.Mask ([])
        return req.then (respond)

    @app.route ("/5")
    def index5 (context):
        reqs = [
            context.Mask ("@pypi/project/rs4/"),
            context.Mask ([{'symbol': 'RHAT'}, {'symbol': 'RHAT'}])
        ]
        return str ([rs.fetch () for rs in context.Tasks (reqs)])

    @app.route ("/6")
    def index6 (context):
        reqs = [
            context.Mask ("@pypi/project/rs4/"),
            context.Mask ([{'symbol': 'RHAT'}, {'symbol': 'RHAT'}])
        ]
        return str (context.Tasks (reqs).fetch ())

    @app.route ("/7")
    def index7 (context):
        reqs = [
            context.Mask ([{'symbol': 'RHAT'}]),
            context.Mask ([{'symbol': 'RHAT'}])
        ]
        return str (context.Tasks (reqs).one ())

    @app.route ("/8")
    def index8 (context):
        reqs = [
            context.Mask ([]),
            context.Mask ([{'symbol': 'RHAT'}])
        ]
        return str (context.Tasks (reqs).one ())

    @app.route ("/11")
    def index11 (context):
        reqs = [
            context.Mask ([]),
            context.Mask ([{'symbol': 'RHAT'}])
        ]
        return str (context.Tasks (reqs).one ())

    @app.route ("/12")
    def index12 (context):
        a = context.Tasks ([context.Mask ([{'symbol': 'RHAT'}])])
        b = context.Tasks ([context.Mask ([{'symbol': 'RHAT'}])])
        a.add (b)
        return str (a.one ())

    @app.route ("/13")
    def index13 (context):
        def respond (context, rss):
            return str (rss.one ())
        a = context.Tasks ([context.Mask ([{'symbol': 'RHAT'}])])
        b = context.Tasks ([context.Mask ([{'symbol': 'RHAT'}])])
        a.merge (b)
        return a.then (respond)

    @app.route ("/14")
    def index14 (context):
        reqs = [
            context.Mask ([]),
            context.Mask ([{'symbol': 'RHAT'}])
        ]
        tasks = context.Tasks (reqs)
        req = context.Mask ([{'symbol': 'RHAT'}])
        (a, b), c = context.Tasks ([tasks, req]).fetch ()
        return str ([a,b,c])

    @app.route ("/15")
    def index15 (context):
        reqs = [
            context.Mask ([]),
            context.Mask ([{'symbol': 'RHAT'}])
        ]
        tasks = context.Tasks (reqs)
        req = context.Mask ([{'symbol': 'RHAT'}])
        mask = context.Mask (['mask'])
        (a, b), c, d = context.Tasks ([tasks, req, mask]).fetch ()
        return str ([a, b, c, d])

    @app.route ("/16")
    def index16 (context):
        reqs = [
            context.Mask ([]),
            context.Mask ([{'symbol': 'RHAT'}])
        ]
        tasks = context.Tasks (reqs)
        req = context.Mask ([{'symbol': 'RHAT'}])
        mask = context.Mask (['mask'])
        th = context.Thread (func1)
        ps = context.Process (func2)
        (a, b), c, d, e, f = context.Tasks ([tasks, req, mask, th, ps]).fetch ()
        return str ([a, b, c, d, e, f])

    @app.route ("/17")
    def index17 (context):
        reqs = [
            context.Mask ([]),
            context.Thread (func1) or context.Mask ('thread')
        ]
        reqs = [
            context.Tasks (reqs),
            context.Mask (['mask']),
            context.Thread (func1),
            context.Process (func2)
        ]
        tasks = context.Tasks (reqs)
        req = context.Mask ([{'symbol': 'RHAT'}])
        mask = context.Mask (['mask'])

        ((a, b), c, d, e), e, f = context.Tasks ([tasks, req, mask]).fetch ()
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
