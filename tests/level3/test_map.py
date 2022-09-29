import skitai
import confutil
import pprint

def test_map (app, dbpath):
    @app.route ("/1")
    def index (context):
        return context.Map (
            a = context.Mask ("/rs4/"),
            b = context.Mask ([{'id': 1, 'symbol': 'RHAT'}, {'id': 2, 'symbol': 'RHAT'}]),
            c = 123
        )

    @app.route ("/2")
    def index2 (context):
        return context.Map (
            context.Mask (456),
            a = context.Mask ("/rs4/"),
            b = context.Mask ([{'id': 2, 'symbol': 'RHAT'}, {'id': 2, 'symbol': 'RHAT'}]),
            c = 123
        )

    @app.route ("/3")
    def index3 (context):
        return context.Map (
            "408 OK",
            context.Mask (456),
            a = 123,
            b = '456',
            c = context.Mask ([{'id': 2, 'symbol': 'RHAT'}, {'id': 2, 'symbol': 'RHAT'}]),
            d = context.Tasks ([
                context.Mask (789),
                context.Mask ('hello')
            ]),
            e = context.Tasks (
                x = context.Mask (789),
                y = context.Mask ('hello')
            ),
            f__y = context.Tasks (
                context.Mask (789),
                y = context.Mask ('hello')
            ),
            g__fetch__1 = context.Tasks (
                context.Mask (789),
                context.Mask ('hello')
            ),
            h = context.Tasks (
                a = context.Mask (789),
                b = context.Tasks (
                    context.Mask (789),
                    context.Mask ('hello')
                )
            ),
        )

    @app.route ("/4")
    def index2 (context):
        return context.Map (
            a = 1,
            b = '2',
            c = 123
        )

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
