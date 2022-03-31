import skitai
import confutil
import pprint

def test_map (app, dbpath):
    @app.route ("/1")
    def index (was):
        return was.Map (
            a = was.stub ('@pypi/project').get ("/rs4/"),
            b = was.Mask ([{'id': 1, 'symbol': 'RHAT'}, {'id': 2, 'symbol': 'RHAT'}]),
            c = 123
        )

    @app.route ("/2")
    def index2 (was):
        return was.Map (
            was.Mask (456),
            a = was.stub ('@pypi/project').get ("/rs4/"),
            b = was.Mask ([{'id': 2, 'symbol': 'RHAT'}, {'id': 2, 'symbol': 'RHAT'}]),
            c = 123
        )

    @app.route ("/3")
    def index3 (was):
        return was.Map (
            "408 OK",
            was.Mask (456),
            a = 123,
            b = '456',
            c = was.Mask ([{'id': 2, 'symbol': 'RHAT'}, {'id': 2, 'symbol': 'RHAT'}]),
            d = was.Tasks ([
                was.Mask (789),
                was.Mask ('hello')
            ]),
            e = was.Tasks (
                x = was.Mask (789),
                y = was.Mask ('hello')
            ),
            f__y = was.Tasks (
                was.Mask (789),
                y = was.Mask ('hello')
            ),
            g__fetch__1 = was.Tasks (
                was.Mask (789),
                was.Mask ('hello')
            ),
            h = was.Tasks (
                a = was.Mask (789),
                b = was.Tasks (
                    was.Mask (789),
                    was.Mask ('hello')
                )
            ),
        )

    @app.route ("/4")
    def index2 (was):
        return was.Map (
            a = 1,
            b = '2',
            c = 123
        )

    app.alias ("@pypi", skitai.PROTO_HTTPS, "pypi.org")

    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/1")
        assert resp.status_code == 200
        assert resp.data ['a'].find ('rs4') != -1
        assert resp.data ['b'][0]['id']
        assert resp.data ['c'] == 123

        resp = cli.get ("/2")
        assert resp.status_code == 200
        assert resp.data ['a'].find ('rs4') != -1
        assert resp.data ['b'][0]['id']
        assert resp.data ['c'] == 123

        resp = cli.get ("/3")
        assert resp.status_code == 408
        assert resp.data ['a'] == 123
        assert resp.data ['b'] == '456'
        assert resp.data ['c'][0]['id']
        assert resp.data ['d'][0] == 789
        assert resp.data ['d'][1] == 'hello'
        assert resp.data ['e']['x'] == 789
        assert resp.data ['e']['y'] == 'hello'
        assert resp.data ['f'] == 'hello'
        assert resp.data ['g'] == 'hello'
        assert resp.data ['h']['a'] == 789
        assert resp.data ['h']['b'][0] == 789
        assert resp.data ['h']['b'][1] == 'hello'

        resp = cli.get ("/4")
        assert resp.status_code == 200
        assert resp.data ['a'] == 1
        assert resp.data ['b'] == '2'
        assert resp.data ['c'] == 123
