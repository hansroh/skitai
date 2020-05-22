Benchmark Code
=========================

May 23, 2020

Django
------------------

.. code:: python

    from django.db.models import Q, Count
    from django.http import JsonResponse

    def bench (request):
        q = (Transaction.objects
            .filter (Q (from_wallet_id = 8) | Q (to_wallet_id = 8)))
        record_count = q.aggregate (Count ('id'))['id__count']
        rows = q.order_by ("-created_at")[:10]
        return JsonResponse (
            {'txs': list(rows.values()), 'record_count': record_count}
        )


Atila
------------------

.. code:: python

    from sqlphile import Q
    @app.route ("/apis/bench", methods = ['GET'])
    def bench (was):
        with was.db ('@mydb') as db:
            root = (db.select ("transaction")
                        .filter (Q (from_wallet_id = 8) | Q (to_wallet_id = 8))
                        .order_by ("-created_at").limit (10))
            qs = [
                root.execute (),
                root.clone ().aggregate ('count (a.id) as cnt').execute ()
            ]
            txs, record_count = was.Tasks (qs).fetch ()

        return was.API (
            txs =  txs,
            record_count = record_count [0].cnt
        )


FastAPI
-----------------

.. code:: python

    pool = None
    @app.on_event("startup")
    async def startup():
        global pool
        pool = await asyncpg.create_pool (user='user', password='password', database='mydb', host='localhost')

    @app.get("/bench")
    async def read_root():
        async def query (q):
            async with pool.acquire() as conn:
                return await conn.fetch (q)

        txs, record_count = await asyncio.gather (
            query ('''SELECT * FROM transaction where from_wallet_id=8 or from_wallet_id=8 order by created_at desc limit 10;'''),
            query ('''SELECT count (*) as cnt FROM transaction where from_wallet_id=8 or from_wallet_id=8;''')
        )
        return {"txs": txs, 'record_count': record_count [0]['cnt']}



Benchmark Tool
=========================

.. code:: bash

    h2load --h1 -n3000 -c64 -t4 http://192.168.0.154:9019/bench



Benchmark Result (3 Runs Each)
======================================

Skitai + Atila
---------------------------------------------

.. code:: python

    skitai.run (port = 9019, ip = "0.0.0.0", workers = 2, threads = 4)

.. code:: bash

finished in 5.51s, 544.32 req/s, 2.48MB/s
requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
traffic: 13.65MB (14310000) total, 281.25KB (288000) headers (space savings 0.00%), 13.27MB (13917000) data
                     min         max         mean         sd        +/- sd
time for request:    19.61ms    175.42ms    116.21ms     11.49ms    91.20%
time for connect:     1.64ms      2.71ms      1.90ms       296us    79.69%
time to 1st byte:    21.15ms    172.01ms    103.40ms     36.00ms    62.50%
req/s           :       8.37        8.89        8.60        0.09    76.56%


finished in 5.61s, 535.12 req/s, 2.43MB/s
requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
traffic: 13.65MB (14310000) total, 281.25KB (288000) headers (space savings 0.00%), 13.27MB (13917000) data
                     min         max         mean         sd        +/- sd
time for request:    18.09ms    238.69ms    114.42ms     18.56ms    90.63%
time for connect:     1.65ms      2.84ms      1.98ms       333us    76.56%
time to 1st byte:    19.61ms    240.33ms    125.11ms     68.93ms    56.25%
req/s           :       8.26        9.37        8.75        0.29    59.38%


finished in 5.72s, 524.23 req/s, 2.38MB/s
requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
traffic: 13.65MB (14310000) total, 281.25KB (288000) headers (space savings 0.00%), 13.27MB (13917000) data
                     min         max         mean         sd        +/- sd
time for request:    17.53ms    270.51ms    114.86ms     20.50ms    91.27%
time for connect:     1.68ms      2.81ms      1.97ms       312us    78.13%
time to 1st byte:    19.04ms    272.19ms    136.70ms     78.55ms    56.25%
req/s           :       8.06        9.55        8.72        0.45    59.38%



Django Dev Server
-------------------------

.. code:: bash

    ./manage.py runserver 0.0.0.0:9019

.. code:: bash

    finished in 26.90s, 111.51 req/s, 552.22KB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.51MB (15213000) total, 471.68KB (483000) headers (space savings 0.00%), 13.92MB (14601000) data
                        min         max         mean         sd        +/- sd
    time for request:    35.14ms       3.61s    552.33ms    184.52ms    92.83%
    time for connect:     1.70ms      2.66ms      1.93ms       252us    79.69%
    time to 1st byte:   101.95ms       3.61s       1.07s    987.16ms    90.63%
    req/s           :       1.71        1.94        1.81        0.06    68.75%


    finished in 33.79s, 88.77 req/s, 439.62KB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.51MB (15213000) total, 471.68KB (483000) headers (space savings 0.00%), 13.92MB (14601000) data
                        min         max         mean         sd        +/- sd
    time for request:    29.89ms       4.44s    686.21ms    297.64ms    85.27%
    time for connect:     1.63ms      2.90ms      2.03ms       328us    64.06%
    time to 1st byte:    63.56ms       4.44s       1.41s       1.37s    84.38%
    req/s           :       1.39        1.61        1.46        0.06    65.63%


    finished in 26.71s, 112.30 req/s, 556.11KB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.51MB (15213000) total, 471.68KB (483000) headers (space savings 0.00%), 13.92MB (14601000) data
                        min         max         mean         sd        +/- sd
    time for request:    36.46ms       3.71s    546.39ms    208.19ms    93.33%
    time for connect:     1.62ms      2.92ms      2.02ms       343us    67.19%
    time to 1st byte:    49.53ms       3.71s       1.17s       1.11s    84.38%
    req/s           :       1.72        1.97        1.83        0.06    65.63%


Skitai + Django
----------------------

.. code:: python

    skitai.run (port = 9019, ip = "0.0.0.0", workers = 2, threads = 4)

.. code:: bash

    finished in 12.45s, 241.03 req/s, 1.18MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.67MB (15384000) total, 421.88KB (432000) headers (space savings 0.00%), 14.14MB (14823000) data
                        min         max         mean         sd        +/- sd
    time for request:    37.22ms    413.54ms    262.01ms     26.78ms    94.10%
    time for connect:     1.61ms      2.69ms      1.90ms       291us    79.69%
    time to 1st byte:    38.71ms    415.13ms    196.65ms    113.29ms    59.38%
    req/s           :       3.72        3.90        3.82        0.05    68.75%


    finished in 13.26s, 226.24 req/s, 1.11MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.67MB (15384000) total, 421.88KB (432000) headers (space savings 0.00%), 14.14MB (14823000) data
                        min         max         mean         sd        +/- sd
    time for request:    40.63ms    448.68ms    270.59ms     27.60ms    91.67%
    time for connect:     1.71ms      2.82ms      1.97ms       288us    81.25%
    time to 1st byte:    42.21ms    450.37ms    213.47ms    124.10ms    62.50%
    req/s           :       3.47        3.90        3.70        0.13    53.13%


    finished in 12.85s, 233.38 req/s, 1.14MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.67MB (15384000) total, 421.88KB (432000) headers (space savings 0.00%), 14.14MB (14823000) data
                        min         max         mean         sd        +/- sd
    time for request:    40.78ms    451.61ms    262.70ms     27.41ms    91.93%
    time for connect:     1.71ms      3.03ms      2.11ms       373us    71.88%
    time to 1st byte:    42.34ms    453.51ms    210.10ms    124.22ms    56.25%
    req/s           :       3.60        4.03        3.81        0.13    53.13%


gunicorn + Django WSGI
---------------------------

.. code:: bash

    gunicorn --bind 0.0.0.0:9019 --workers 2 --threads 4 orm.wsgi

.. code:: bash

    finished in 12.14s, 247.19 req/s, 1.22MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.75MB (15468000) total, 492.19KB (504000) headers (space savings 0.00%), 14.14MB (14823000) data
                        min         max         mean         sd        +/- sd
    time for request:    70.11ms    334.35ms    247.48ms     21.04ms    85.27%
    time for connect:     1.48ms      2.92ms      1.93ms       400us    70.31%
    time to 1st byte:    72.80ms    312.07ms    187.28ms     71.35ms    59.38%
    req/s           :       3.87        4.24        4.05        0.15    53.13%


    finished in 12.56s, 238.77 req/s, 1.17MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.75MB (15468000) total, 492.19KB (504000) headers (space savings 0.00%), 14.14MB (14823000) data
                        min         max         mean         sd        +/- sd
    time for request:    28.64ms    343.74ms    249.10ms     27.93ms    83.83%
    time for connect:     1.66ms      2.76ms      1.92ms       282us    79.69%
    time to 1st byte:    30.92ms    302.33ms    150.02ms     72.33ms    62.50%
    req/s           :       3.73        4.38        4.03        0.28    56.25%


    finished in 13.45s, 223.04 req/s, 1.10MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.75MB (15468000) total, 492.19KB (504000) headers (space savings 0.00%), 14.14MB (14823000) data
                        min         max         mean         sd        +/- sd
    time for request:    28.90ms    357.32ms    254.04ms     41.18ms    67.33%
    time for connect:     1.62ms      2.76ms      1.88ms       287us    81.25%
    time to 1st byte:    30.33ms    295.33ms    152.65ms     74.32ms    59.38%
    req/s           :       3.49        4.68        4.01        0.56    56.25%



uvicorn + Django ASGI
------------------------

.. code:: bash

    uvicorn orm.asgi:application --host 0.0.0.0 --port 9019 --workers 2

.. code:: bash

    finished in 14.30s, 209.75 req/s, 1.02MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.66MB (15372000) total, 410.16KB (420000) headers (space savings 0.00%), 14.14MB (14823000) data
                        min         max         mean         sd        +/- sd
    time for request:    26.73ms    489.37ms    265.31ms     64.07ms    69.53%
    time for connect:     1.52ms      2.65ms      1.79ms       298us    79.69%
    time to 1st byte:   227.36ms    387.08ms    326.96ms     55.53ms    53.13%
    req/s           :       3.28        4.77        3.86        0.60    60.94%


    finished in 12.63s, 237.53 req/s, 1.16MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.66MB (15372000) total, 410.16KB (420000) headers (space savings 0.00%), 14.14MB (14823000) data
                        min         max         mean         sd        +/- sd
    time for request:    35.28ms    557.75ms    258.50ms     48.83ms    76.23%
    time for connect:     1.61ms      2.69ms      1.87ms       293us    79.69%
    time to 1st byte:    77.72ms    270.50ms    231.23ms     58.58ms    85.94%
    req/s           :       3.69        4.09        3.87        0.11    59.38%


    finished in 13.90s, 215.90 req/s, 1.06MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.66MB (15372000) total, 410.16KB (420000) headers (space savings 0.00%), 14.14MB (14823000) data
                        min         max         mean         sd        +/- sd
    time for request:    30.53ms    453.71ms    263.47ms     57.86ms    71.87%
    time for connect:     1.67ms      2.80ms      1.93ms       289us    81.25%
    time to 1st byte:    57.63ms    283.51ms    231.53ms     51.15ms    84.38%
    req/s           :       3.33        4.54        3.85        0.48    56.25%


uvicorn + FastAPI
------------------------

.. code:: bash

    uvicorn fastapiapp:app --host 0.0.0.0 --port 9019 --workers 2

.. code:: bash

finished in 5.54s, 541.59 req/s, 2.45MB/s
requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
traffic: 13.60MB (14256000) total, 269.53KB (276000) headers (space savings 0.00%), 13.23MB (13875000) data
                     min         max         mean         sd        +/- sd
time for request:     8.96ms    370.88ms    111.16ms     51.11ms    73.30%
time for connect:     1.63ms      2.69ms      1.90ms       281us    79.69%
time to 1st byte:    52.15ms    287.15ms    123.83ms     51.04ms    67.19%
req/s           :       8.45        9.95        9.01        0.36    62.50%


finished in 5.61s, 534.36 req/s, 2.42MB/s
requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
traffic: 13.60MB (14256000) total, 269.53KB (276000) headers (space savings 0.00%), 13.23MB (13875000) data
                     min         max         mean         sd        +/- sd
time for request:     8.99ms    578.86ms     99.85ms     74.99ms    68.43%
time for connect:     1.62ms      2.76ms      1.92ms       312us    78.13%
time to 1st byte:    39.38ms    280.43ms    116.70ms     61.46ms    73.44%
req/s           :       8.20       17.18       10.88        3.53    71.88%


finished in 5.47s, 548.20 req/s, 2.48MB/s
requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
traffic: 13.60MB (14256000) total, 269.53KB (276000) headers (space savings 0.00%), 13.23MB (13875000) data
                     min         max         mean         sd        +/- sd
time for request:     9.12ms    433.58ms    113.01ms     53.04ms    76.33%
time for connect:      872us      1.17ms      1.01ms        88us    53.13%
time to 1st byte:    41.40ms    274.98ms    120.22ms     50.28ms    67.19%
req/s           :       8.43        9.66        8.86        0.29    73.44%

