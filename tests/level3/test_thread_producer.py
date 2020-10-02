import skitai
import confutil
import pprint
from skitai import was as the_was

GENSQL = '''SELECT 'a', 1
   FROM (SELECT * FROM (
         (SELECT 0 UNION ALL SELECT 1) t2,
         (SELECT 0 UNION ALL SELECT 1) t4,
         (SELECT 0 UNION ALL SELECT 1) t8,
         (SELECT 0 UNION ALL SELECT 1) t16,
         (SELECT 0 UNION ALL SELECT 1) t32,
         (SELECT 0 UNION ALL SELECT 1) t64,
         (SELECT 0 UNION ALL SELECT 1) t128,
         (SELECT 0 UNION ALL SELECT 1) t256,
         (SELECT 0 UNION ALL SELECT 1) t512,
         (SELECT 0 UNION ALL SELECT 1) t1024,
         (SELECT 0 UNION ALL SELECT 1) t2048
         )
    )
'''

def test_map (app, dbpath):
    @app.route ("/1")
    def index (was):
        def producer (cur):
            def produce (q):
                rows = cur.fetchmany (3)
                q.put (str (rows))
                q.put (None)
                cur.close ()
            return produce

        cur = the_was.cursor ("@sqlite").execute (GENSQL)
        return was.Queue (producer (cur))

    app.alias ("@sqlite", skitai.DB_SQLITE3, dbpath)
    with app.test_client ("/", confutil.getroot ()) as cli:
        resp = cli.get ("/1")
        assert resp.status_code == 200
