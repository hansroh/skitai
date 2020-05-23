Benchmark Overview
=========================

May 23, 2020


Installation
-----------------------

.. code:: bash

    export MYDB="user:passwd@192.168.0.80/bench"
    ./install.sh


Test Environment
----------------------------

Database Server

- 4 CPU
- PostgreSQL 9.6

Test Servers & Benchmark Tool

- 20 CPUs
- h2load

Benchmark Command

.. code:: bash

    h2load --h1 -n3000 -c64 -t4 http://192.168.0.100:9019/bench

    # HTTP/2.0
    h2load -m2 -n3000 -c64 -t4 http://192.168.0.154:9007/bench


.. contents:: Table of Contents


Benchmark Results
=====================

Warming Up
--------------------

Django Dev Server
`````````````````````````

.. code:: bash

    ./run-django.sh

.. code:: bash

    finished in 24.97s, 120.13 req/s, 595.49KB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.52MB (15228000) total, 471.68KB (483000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    33.73ms       3.73s    508.85ms    211.36ms    92.93%
    time for connect:     1.68ms      2.74ms      1.94ms       283us    79.69%
    time to 1st byte:    95.96ms       3.73s       1.18s       1.12s    87.50%
    req/s           :       1.88        2.14        1.97        0.07    67.19%


    finished in 24.91s, 120.46 req/s, 597.10KB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.52MB (15228000) total, 471.68KB (483000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    28.42ms       3.60s    507.75ms    204.29ms    92.70%
    time for connect:     1.69ms      2.66ms      1.93ms       250us    81.25%
    time to 1st byte:    66.39ms       3.60s       1.17s       1.08s    82.81%
    req/s           :       1.85        2.15        1.97        0.08    68.75%


    finished in 24.90s, 120.51 req/s, 597.35KB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.52MB (15228000) total, 471.68KB (483000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    30.03ms       3.53s    509.52ms    185.59ms    93.40%
    time for connect:     1.57ms      2.61ms      1.82ms       271us    79.69%
    time to 1st byte:    64.10ms       3.53s       1.03s       1.00s    89.06%
    req/s           :       1.87        2.12        1.96        0.06    65.63%



2 Workers 4 Threads if possible, 3 Runs Each
-------------------------------------------------------

Gunicorn + Django WSGI
`````````````````````````

.. code:: bash

    ./run-gunicorn-django.sh

.. code:: bash

    finished in 14.95s, 200.72 req/s, 997.12KB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.55MB (15261000) total, 492.19KB (504000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    70.30ms    527.85ms    292.19ms     50.11ms    75.43%
    time for connect:     1.64ms      2.72ms      1.94ms       279us    78.13%
    time to 1st byte:    72.16ms    382.40ms    209.96ms     91.14ms    59.38%
    req/s           :       3.13        3.83        3.45        0.31    59.38%


    finished in 14.62s, 205.25 req/s, 1019.63KB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.55MB (15261000) total, 492.19KB (504000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    36.75ms    540.07ms    285.64ms     46.17ms    81.80%
    time for connect:     1.26ms      2.41ms      1.54ms       318us    81.25%
    time to 1st byte:    38.80ms    372.22ms    192.74ms     91.11ms    64.06%
    req/s           :       3.20        3.92        3.53        0.32    57.81%


    finished in 14.28s, 210.09 req/s, 1.02MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.55MB (15261000) total, 492.19KB (504000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    32.52ms    441.14ms    284.37ms     41.38ms    82.77%
    time for connect:     1.61ms      2.70ms      1.86ms       273us    81.25%
    time to 1st byte:    34.00ms    316.16ms    166.75ms     80.38ms    54.69%
    req/s           :       3.28        3.82        3.53        0.23    59.38%



Uvicorn + Django ASGI
`````````````````````````

.. code:: bash

    ./run-uvicorn-django.sh

.. code:: bash

    finished in 14.83s, 202.26 req/s, 998.45KB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.46MB (15165000) total, 410.16KB (420000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    31.93ms    559.88ms    263.42ms     79.96ms    64.93%
    time for connect:     1.65ms      2.80ms      1.95ms       311us    79.69%
    time to 1st byte:   160.33ms    561.37ms    361.86ms    108.66ms    48.44%
    req/s           :       3.13        5.89        4.08        1.17    64.06%


    finished in 12.64s, 237.40 req/s, 1.14MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.46MB (15165000) total, 410.16KB (420000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    18.71ms    509.82ms    244.72ms     46.83ms    77.17%
    time for connect:     1.61ms      2.73ms      1.87ms       283us    81.25%
    time to 1st byte:   145.29ms    291.65ms    243.70ms     37.21ms    51.56%
    req/s           :       3.67        4.65        4.12        0.39    50.00%


    finished in 14.85s, 201.96 req/s, 996.96KB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.46MB (15165000) total, 410.16KB (420000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    29.95ms    577.38ms    264.16ms     78.14ms    61.23%
    time for connect:     1.60ms      2.76ms      1.88ms       299us    81.25%
    time to 1st byte:    62.56ms    320.32ms    258.48ms     68.48ms    68.75%
    req/s           :       3.10        5.84        4.08        1.19    64.06%



Uvicorn + FastAPI
`````````````````````````

.. code:: bash

    ./run-uvicorn-fastapi.sh

.. code:: bash

    finished in 5.88s, 510.35 req/s, 2.32MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.61MB (14271000) total, 269.53KB (276000) headers (space savings 0.00%), 13.25MB (13890000) data
                        min         max         mean         sd        +/- sd
    time for request:     9.36ms    730.16ms    100.24ms     84.43ms    86.57%
    time for connect:     1.64ms      2.79ms      1.92ms       308us    81.25%
    time to 1st byte:    38.96ms    591.63ms    138.66ms    101.86ms    89.06%
    req/s           :       7.86       17.55       10.86        3.45    67.19%


    finished in 5.72s, 524.21 req/s, 2.38MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.61MB (14271000) total, 269.53KB (276000) headers (space savings 0.00%), 13.25MB (13890000) data
                        min         max         mean         sd        +/- sd
    time for request:     7.89ms    597.29ms    100.95ms     73.84ms    72.00%
    time for connect:     1.62ms      2.70ms      1.89ms       295us    79.69%
    time to 1st byte:    41.13ms    354.28ms    130.59ms     73.50ms    75.00%
    req/s           :       8.14       14.03       10.32        2.18    64.06%


    finished in 5.84s, 513.55 req/s, 2.33MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.61MB (14271000) total, 269.53KB (276000) headers (space savings 0.00%), 13.25MB (13890000) data
                        min         max         mean         sd        +/- sd
    time for request:     8.97ms    668.46ms    100.57ms     79.78ms    81.87%
    time for connect:     1.70ms      2.80ms      1.97ms       278us    81.25%
    time to 1st byte:    31.83ms    376.24ms    129.73ms     81.37ms    76.56%
    req/s           :       7.99       17.54       10.69        3.11    67.19%


Skitai + Django WSGI
`````````````````````````

.. code:: python

    ./run-skitai-django.py

.. code:: bash

    finished in 13.56s, 221.28 req/s, 1.07MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.47MB (15177000) total, 421.88KB (432000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    79.73ms    478.70ms    285.69ms     34.52ms    90.03%
    time for connect:     1.62ms      2.68ms      1.89ms       282us    79.69%
    time to 1st byte:    82.11ms    345.54ms    212.29ms     78.92ms    56.25%
    req/s           :       3.43        3.55        3.50        0.03    64.06%


    finished in 15.70s, 191.10 req/s, 944.10KB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.47MB (15177000) total, 421.88KB (432000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    43.60ms    561.01ms    294.07ms     62.26ms    75.53%
    time for connect:     1.70ms      2.85ms      1.97ms       295us    79.69%
    time to 1st byte:    50.66ms    427.07ms    193.47ms    109.37ms    64.06%
    req/s           :       2.96        4.19        3.48        0.55    57.81%


    finished in 14.65s, 204.72 req/s, 1011.38KB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.47MB (15177000) total, 421.88KB (432000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    41.42ms    551.75ms    290.73ms     50.71ms    86.63%
    time for connect:     1.65ms      2.78ms      1.91ms       286us    81.25%
    time to 1st byte:    42.97ms    385.95ms    186.15ms     95.99ms    59.38%
    req/s           :       3.17        3.77        3.46        0.24    57.81%


Sanic
`````````````````````````

.. code:: python

     ./run_sanic.py


.. code:: bash


    finished in 4.16s, 721.36 req/s, 3.39MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.11MB (14796000) total, 143.55KB (147000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     6.86ms    349.64ms     79.33ms     32.50ms    80.20%
    time for connect:     1.61ms      2.73ms      1.87ms       295us    81.25%
    time to 1st byte:    37.23ms    351.25ms    113.95ms     53.09ms    78.13%
    req/s           :      11.23       15.45       12.80        1.67    64.06%


    finished in 4.50s, 667.25 req/s, 3.14MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.11MB (14796000) total, 143.55KB (147000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     6.78ms    377.62ms     82.54ms     45.56ms    77.23%
    time for connect:     1.54ms      2.69ms      1.81ms       286us    81.25%
    time to 1st byte:    31.97ms    327.17ms    124.98ms     70.86ms    65.63%
    req/s           :      10.46       18.40       12.73        3.09    70.31%


    finished in 4.02s, 746.15 req/s, 3.51MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.11MB (14796000) total, 143.55KB (147000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     6.37ms    290.62ms     73.06ms     34.24ms    77.93%
    time for connect:     1.65ms      2.71ms      1.90ms       287us    79.69%
    time to 1st byte:    30.45ms    278.28ms     85.61ms     46.55ms    76.56%
    req/s           :      11.51       20.49       14.41        3.58    68.75%



Uvicorn + Sanic
`````````````````````````

.. code:: python

     ./run-uvicorn-sanic.sh


.. code:: bash

    finished in 4.35s, 688.91 req/s, 3.26MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.21MB (14901000) total, 234.38KB (240000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     6.42ms    283.03ms     80.73ms     39.22ms    79.87%
    time for connect:     2.43ms      3.89ms      2.88ms       406us    65.63%
    time to 1st byte:    47.08ms    236.52ms    129.74ms     48.54ms    67.19%
    req/s           :      10.63       16.92       12.81        2.50    65.63%


    finished in 4.21s, 712.97 req/s, 3.38MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.21MB (14901000) total, 234.38KB (240000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     7.33ms    288.61ms     76.27ms     40.78ms    77.27%
    time for connect:     1.62ms      2.73ms      1.89ms       292us    81.25%
    time to 1st byte:    32.25ms    240.57ms     93.08ms     50.89ms    68.75%
    req/s           :      10.93       22.01       14.16        4.46    71.88%


    finished in 4.62s, 648.74 req/s, 3.07MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.21MB (14901000) total, 234.38KB (240000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     7.10ms    288.56ms     83.71ms     39.09ms    81.93%
    time for connect:     1.59ms      2.72ms      1.87ms       293us    81.25%
    time to 1st byte:    32.64ms    235.88ms     89.57ms     42.90ms    76.56%
    req/s           :      10.15       18.37       12.66        3.32    67.19%



Gunicorn + Sanic
`````````````````````````

.. code:: python

     ./run-uvicorn-sanic.sh

.. code:: bash

    finished in 4.22s, 711.17 req/s, 3.35MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.11MB (14796000) total, 143.55KB (147000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     7.49ms    264.36ms     78.63ms     31.37ms    83.53%
    time for connect:     1.62ms      3.41ms      2.16ms       485us    68.75%
    time to 1st byte:    39.19ms    227.61ms     95.53ms     36.10ms    67.19%
    req/s           :      10.91       16.82       13.07        2.26    62.50%


    finished in 4.31s, 695.69 req/s, 3.27MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.11MB (14796000) total, 143.55KB (147000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     6.50ms    383.73ms     78.52ms     37.58ms    82.30%
    time for connect:     1.62ms      2.71ms      1.88ms       287us    79.69%
    time to 1st byte:    30.20ms    158.20ms     83.35ms     33.64ms    64.06%
    req/s           :      10.76       18.84       13.37        3.18    67.19%


    finished in 4.11s, 729.51 req/s, 3.43MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.11MB (14796000) total, 143.55KB (147000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     6.86ms    352.79ms     75.82ms     35.96ms    83.60%
    time for connect:     1.62ms      2.74ms      1.86ms       292us    81.25%
    time to 1st byte:    38.43ms    218.12ms     89.65ms     40.09ms    68.75%
    req/s           :      11.25       18.78       13.68        2.79    65.63%




Skitai + Atila I
`````````````````````````

.. code:: python

    ./run-skitai-atila.py
    # URI: /bench

.. code:: bash

    finished in 5.49s, 546.10 req/s, 2.43MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.34MB (13983000) total, 281.25KB (288000) headers (space savings 0.00%), 12.96MB (13590000) data
                        min         max         mean         sd        +/- sd
    time for request:    25.22ms    181.25ms    115.38ms     13.46ms    83.17%
    time for connect:     1.75ms      3.01ms      2.12ms       333us    70.31%
    time to 1st byte:    27.87ms    183.04ms     97.22ms     42.11ms    60.94%
    req/s           :       8.42        8.85        8.66        0.08    68.75%


    finished in 5.75s, 521.44 req/s, 2.32MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.34MB (13983000) total, 281.25KB (288000) headers (space savings 0.00%), 12.96MB (13590000) data
                        min         max         mean         sd        +/- sd
    time for request:    28.81ms    235.86ms    118.83ms     19.68ms    89.43%
    time for connect:     1.61ms      3.44ms      2.22ms       549us    67.19%
    time to 1st byte:    32.08ms    140.64ms     85.90ms     32.77ms    59.38%
    req/s           :       8.06        8.83        8.42        0.22    62.50%


    finished in 5.56s, 539.51 req/s, 2.40MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.34MB (13983000) total, 281.25KB (288000) headers (space savings 0.00%), 12.96MB (13590000) data
                        min         max         mean         sd        +/- sd
    time for request:    29.39ms    161.41ms    117.05ms     12.60ms    77.07%
    time for connect:     1.41ms      1.84ms      1.62ms       122us    56.25%
    time to 1st byte:    30.64ms    158.25ms     92.47ms     37.58ms    60.94%
    req/s           :       8.38        8.71        8.54        0.07    68.75%



Skitai + Atila II
`````````````````````````

.. code:: python

     ./run-skitai-atila.py
     # URL: /bench2

.. code:: bash

    finished in 6.67s, 449.77 req/s, 2.00MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.34MB (13983000) total, 281.25KB (288000) headers (space savings 0.00%), 12.96MB (13590000) data
                        min         max         mean         sd        +/- sd
    time for request:    12.42ms    218.07ms    133.61ms     18.94ms    79.13%
    time for connect:     1.71ms      3.03ms      2.13ms       364us    62.50%
    time to 1st byte:    31.35ms    178.34ms     97.19ms     38.55ms    62.50%
    req/s           :       6.96        8.10        7.51        0.45    54.69%


    finished in 6.56s, 457.02 req/s, 2.03MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.34MB (13983000) total, 281.25KB (288000) headers (space savings 0.00%), 12.96MB (13590000) data
                        min         max         mean         sd        +/- sd
    time for request:    29.84ms    211.25ms    130.90ms     17.84ms    77.87%
    time for connect:     1.61ms      2.74ms      1.88ms       286us    81.25%
    time to 1st byte:    31.30ms    179.11ms     92.13ms     37.58ms    60.94%
    req/s           :       7.11        8.41        7.67        0.50    60.94%


    finished in 6.51s, 460.87 req/s, 2.05MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.34MB (13983000) total, 281.25KB (288000) headers (space savings 0.00%), 12.96MB (13590000) data
                        min         max         mean         sd        +/- sd
    time for request:    30.85ms    231.59ms    133.71ms     18.55ms    85.63%
    time for connect:     1.56ms      3.03ms      1.98ms       436us    75.00%
    time to 1st byte:    33.17ms    169.65ms    103.67ms     40.93ms    56.25%
    req/s           :       7.12        7.84        7.48        0.23    56.25%



Skitai + Atila I with HTTP/2.0
``````````````````````````````````````

.. code:: python

    ./run-skitai-atila.py
    # URI: /bench2

.. code:: bash

    finished in 6.12s, 490.54 req/s, 2.13MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.04MB (13674744) total, 26.27KB (26904) headers (space savings 91.54%), 12.96MB (13590000) data
                        min         max         mean         sd        +/- sd
    time for request:    47.58ms    434.50ms    252.77ms     30.40ms    92.27%
    time for connect:     1.60ms      2.74ms      1.90ms       280us    79.69%
    time to 1st byte:    49.34ms    433.69ms    235.78ms    114.79ms    56.25%
    req/s           :       7.57        8.15        7.82        0.14    68.75%


    finished in 6.18s, 485.37 req/s, 2.11MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.04MB (13674721) total, 26.25KB (26881) headers (space savings 91.55%), 12.96MB (13590000) data
                        min         max         mean         sd        +/- sd
    time for request:    37.29ms    426.25ms    256.71ms     42.05ms    89.50%
    time for connect:     1.48ms      2.62ms      1.79ms       283us    81.25%
    time to 1st byte:    38.84ms    407.80ms    215.66ms     99.72ms    59.38%
    req/s           :       7.49        8.06        7.70        0.11    76.56%


    finished in 6.22s, 482.37 req/s, 2.10MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.04MB (13674169) total, 25.71KB (26329) headers (space savings 91.72%), 12.96MB (13590000) data
                        min         max         mean         sd        +/- sd
    time for request:    46.76ms    450.07ms    257.67ms     43.76ms    89.57%
    time for connect:     1.64ms      2.74ms      1.93ms       275us    81.25%
    time to 1st byte:    49.41ms    444.10ms    233.33ms    115.20ms    59.38%
    req/s           :       7.43        7.97        7.67        0.12    71.88%



4 Workers 4 Threads if possible, 3 Runs Each
-----------------------------------------------------

Same number of workers with database CPUs.

Gunicorn + Django WSGI
`````````````````````````

.. code:: bash

    ./run-gunicorn-django.sh

.. code:: bash

    finished in 10.84s, 276.82 req/s, 1.34MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.55MB (15261000) total, 492.19KB (504000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    46.88ms    431.56ms    199.85ms     40.87ms    72.50%
    time for connect:     2.13ms      3.15ms      2.40ms       262us    78.13%
    time to 1st byte:    66.32ms    335.84ms    177.42ms     63.99ms    65.63%
    req/s           :       4.29        5.74        5.05        0.49    50.00%


    finished in 10.28s, 291.73 req/s, 1.42MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.55MB (15261000) total, 492.19KB (504000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    32.42ms    495.81ms    206.42ms     48.56ms    78.20%
    time for connect:     1.66ms      3.00ms      2.10ms       372us    59.38%
    time to 1st byte:    33.83ms    229.04ms    134.48ms     57.14ms    59.38%
    req/s           :       4.50        5.56        4.87        0.34    75.00%


    finished in 10.55s, 284.45 req/s, 1.38MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.55MB (15261000) total, 492.19KB (504000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    27.05ms    561.94ms    204.77ms     48.01ms    80.80%
    time for connect:     1.66ms      2.92ms      2.04ms       341us    68.75%
    time to 1st byte:    35.19ms    260.08ms    149.64ms     60.34ms    60.94%
    req/s           :       4.40        5.62        4.91        0.37    51.56%



Uvicorn + Django ASGI
`````````````````````````

.. code:: bash

    ./run-uvicorn-django.sh

.. code:: bash

    finished in 7.78s, 385.74 req/s, 1.86MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.46MB (15165000) total, 410.16KB (420000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    13.79ms    625.11ms    146.23ms    116.49ms    70.13%
    time for connect:     1.60ms      2.65ms      1.83ms       255us    81.25%
    time to 1st byte:    80.21ms    322.45ms    195.34ms     65.44ms    60.94%
    req/s           :       6.04        8.64        6.89        0.62    70.31%


    finished in 7.24s, 414.31 req/s, 2.00MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.46MB (15165000) total, 410.16KB (420000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    14.67ms    529.88ms    145.47ms     65.06ms    77.30%
    time for connect:     1.63ms      2.72ms      1.88ms       279us    81.25%
    time to 1st byte:    37.29ms    224.75ms    153.40ms     32.88ms    81.25%
    req/s           :       6.49       31.39        7.19        3.09    98.44%


    finished in 7.76s, 386.80 req/s, 1.86MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.46MB (15165000) total, 410.16KB (420000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    13.95ms    897.37ms    154.09ms    105.71ms    77.57%
    time for connect:     2.00ms      3.12ms      2.28ms       310us    78.13%
    time to 1st byte:    27.40ms    692.34ms    236.22ms    162.99ms    73.44%
    req/s           :       5.99       39.46        6.94        4.14    98.44%



Uvicorn + FastAPI
`````````````````````````

.. code:: bash

    ./run-uvicorn-fastapi.sh

.. code:: bash

    finished in 4.50s, 666.42 req/s, 3.02MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.61MB (14271000) total, 269.53KB (276000) headers (space savings 0.00%), 13.25MB (13890000) data
                        min         max         mean         sd        +/- sd
    time for request:    10.34ms    289.39ms     86.23ms     38.93ms    71.63%
    time for connect:     1.57ms      2.61ms      1.83ms       269us    81.25%
    time to 1st byte:    62.84ms    184.93ms    113.85ms     29.51ms    60.94%
    req/s           :      10.27       13.79       11.70        1.17    67.19%


    finished in 4.56s, 658.50 req/s, 2.99MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.61MB (14271000) total, 269.53KB (276000) headers (space savings 0.00%), 13.25MB (13890000) data
                        min         max         mean         sd        +/- sd
    time for request:     8.80ms    333.82ms     88.57ms     42.54ms    69.53%
    time for connect:     1.61ms      2.74ms      1.88ms       292us    81.25%
    time to 1st byte:    43.19ms    335.47ms    125.82ms     60.16ms    73.44%
    req/s           :      10.32       32.17       11.54        2.71    98.44%


    finished in 4.44s, 676.23 req/s, 3.07MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.61MB (14271000) total, 269.53KB (276000) headers (space savings 0.00%), 13.25MB (13890000) data
                        min         max         mean         sd        +/- sd
    time for request:     9.59ms    347.62ms     89.12ms     44.65ms    68.13%
    time for connect:     1.61ms      2.74ms      1.88ms       293us    81.25%
    time to 1st byte:    33.00ms    214.65ms     95.07ms     39.77ms    67.19%
    req/s           :      10.44       31.20       11.43        2.54    98.44%



Skitai + Django WSGI
`````````````````````````

.. code:: python

    ./run-skitai-django.py

.. code:: bash

    finished in 10.80s, 277.72 req/s, 1.34MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.47MB (15177000) total, 421.88KB (432000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    27.43ms    468.88ms    204.26ms     48.75ms    78.23%
    time for connect:     1.67ms      2.65ms      1.91ms       256us    79.69%
    time to 1st byte:    62.81ms    342.86ms    193.47ms     78.95ms    57.81%
    req/s           :       4.31        5.51        4.93        0.41    50.00%


    finished in 10.84s, 276.83 req/s, 1.34MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.47MB (15177000) total, 421.88KB (432000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    34.26ms    485.42ms    197.36ms     55.14ms    73.00%
    time for connect:     1.70ms      2.83ms      1.96ms       293us    81.25%
    time to 1st byte:    39.96ms    269.43ms    147.76ms     62.32ms    62.50%
    req/s           :       4.28        6.62        5.17        0.77    51.56%


    finished in 11.79s, 254.37 req/s, 1.23MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.47MB (15177000) total, 421.88KB (432000) headers (space savings 0.00%), 13.94MB (14616000) data
                        min         max         mean         sd        +/- sd
    time for request:    38.70ms    540.12ms    208.08ms     60.86ms    81.43%
    time for connect:     1.61ms      2.72ms      1.86ms       278us    81.25%
    time to 1st byte:    40.19ms    528.76ms    256.25ms    122.79ms    59.38%
    req/s           :       3.94        5.58        4.90        0.64    60.94%


Sanic
`````````````````````````

.. code:: python

     ./run_sanic.py


.. code:: bash

    finished in 4.57s, 655.76 req/s, 3.08MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.11MB (14796000) total, 143.55KB (147000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     7.29ms    230.66ms     92.36ms     26.16ms    72.53%
    time for connect:     1.67ms      2.81ms      1.94ms       310us    79.69%
    time to 1st byte:    53.32ms    186.93ms    113.73ms     31.46ms    73.44%
    req/s           :      10.09       12.60       10.87        0.75    76.56%


    finished in 4.61s, 651.41 req/s, 3.06MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.11MB (14796000) total, 143.55KB (147000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     7.17ms    242.25ms     92.78ms     29.00ms    76.97%
    time for connect:     1.66ms      2.78ms      1.94ms       285us    81.25%
    time to 1st byte:    27.30ms    212.04ms    101.37ms     42.29ms    65.63%
    req/s           :      10.09       35.01       11.05        3.07    98.44%


    finished in 3.83s, 782.86 req/s, 3.68MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.11MB (14796000) total, 143.55KB (147000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     7.29ms    169.38ms     79.26ms     18.32ms    83.73%
    time for connect:     1.57ms      2.66ms      1.84ms       297us    79.69%
    time to 1st byte:    35.48ms    147.87ms     77.98ms     26.55ms    62.50%
    req/s           :      12.27       44.43       12.97        4.00    98.44%



Uvicorn + Sanic
`````````````````````````

.. code:: python

     ./run-uvicorn-sanic.sh


.. code:: bash


    finished in 4.52s, 663.31 req/s, 3.14MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.21MB (14901000) total, 234.38KB (240000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     7.02ms    267.54ms     90.55ms     29.81ms    76.53%
    time for connect:     1.68ms      2.79ms      1.95ms       309us    79.69%
    time to 1st byte:    44.61ms    201.63ms    107.91ms     33.93ms    73.44%
    req/s           :      10.28       31.97       11.89        5.06    93.75%


    finished in 3.88s, 773.79 req/s, 3.67MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.21MB (14901000) total, 234.38KB (240000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     7.15ms    233.40ms     79.70ms     19.68ms    84.37%
    time for connect:     1.78ms      2.79ms      2.04ms       271us    81.25%
    time to 1st byte:    16.19ms    235.07ms    122.04ms     35.03ms    81.25%
    req/s           :      11.93       44.79       12.91        4.06    98.44%


    finished in 4.10s, 731.52 req/s, 3.47MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.21MB (14901000) total, 234.38KB (240000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     7.18ms    246.48ms     79.12ms     24.06ms    77.97%
    time for connect:     1.62ms      2.74ms      1.88ms       280us    79.69%
    time to 1st byte:    13.63ms    140.73ms     80.99ms     28.00ms    60.94%
    req/s           :      11.24       45.31       13.06        4.19    98.44%


Gunicorn + Sanic
`````````````````````````

.. code:: python

     ./run-uvicorn-sanic.sh

.. code:: bash


    finished in 3.97s, 755.09 req/s, 3.55MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.11MB (14796000) total, 143.55KB (147000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     7.02ms    257.71ms     81.55ms     22.05ms    80.03%
    time for connect:     1.69ms      2.78ms      1.94ms       275us    81.25%
    time to 1st byte:    46.71ms    150.32ms     97.00ms     28.17ms    59.38%
    req/s           :      11.66       38.90       12.55        3.36    98.44%


    finished in 4.13s, 727.22 req/s, 3.42MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.11MB (14796000) total, 143.55KB (147000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     7.38ms    246.54ms     85.36ms     26.28ms    79.93%
    time for connect:     1.59ms      2.72ms      1.86ms       281us    81.25%
    time to 1st byte:    30.31ms    175.60ms     80.72ms     29.02ms    60.94%
    req/s           :      11.20       42.49       12.06        3.87    98.44%


    finished in 3.83s, 782.52 req/s, 3.68MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.11MB (14796000) total, 143.55KB (147000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     7.41ms    194.54ms     78.05ms     19.97ms    81.07%
    time for connect:     1.64ms      2.59ms      1.88ms       245us    81.25%
    time to 1st byte:    31.81ms    125.56ms     78.40ms     26.44ms    62.50%
    req/s           :      12.04       42.90       13.15        3.79    98.44%




Skitai + Atila I
`````````````````````````

.. code:: python

    ./run-skitai-atila.py
    # URI: /bench

.. code:: bash

    finished in 4.24s, 707.62 req/s, 3.36MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.26MB (14949000) total, 281.25KB (288000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     8.75ms    152.41ms     77.22ms     21.09ms    71.23%
    time for connect:     1.69ms      2.80ms      2.04ms       284us    64.06%
    time to 1st byte:    30.13ms    153.85ms     77.51ms     32.37ms    60.94%
    req/s           :      10.93       23.12       13.65        3.82    85.94%


    finished in 4.92s, 609.99 req/s, 2.90MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.26MB (14949000) total, 281.25KB (288000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:    10.25ms    240.99ms     86.77ms     28.00ms    69.17%
    time for connect:     1.67ms      2.75ms      1.92ms       279us    81.25%
    time to 1st byte:    32.79ms    181.80ms     87.49ms     38.59ms    62.50%
    req/s           :       9.39       17.17       12.01        2.60    81.25%


    finished in 3.85s, 778.90 req/s, 3.70MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.26MB (14949000) total, 281.25KB (288000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     8.66ms    148.35ms     79.44ms     15.69ms    73.20%
    time for connect:     1.57ms      2.67ms      1.85ms       296us    79.69%
    time to 1st byte:    21.88ms    140.94ms     78.47ms     32.17ms    62.50%
    req/s           :      11.97       13.62       12.59        0.40    75.00%



Skitai + Atila II
`````````````````````````

.. code:: python

     ./run-skitai-atila.py
     # URL: /bench2

.. code:: bash

    finished in 4.73s, 634.70 req/s, 3.02MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.26MB (14949000) total, 281.25KB (288000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     9.58ms    222.42ms     91.99ms     24.16ms    73.67%
    time for connect:     1.26ms      2.37ms      1.54ms       311us    78.13%
    time to 1st byte:    28.31ms    126.56ms     72.50ms     25.87ms    64.06%
    req/s           :       9.78       11.78       10.90        0.59    60.94%


    finished in 4.96s, 605.21 req/s, 2.88MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.26MB (14949000) total, 281.25KB (288000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     9.07ms    277.68ms     91.40ms     29.79ms    71.13%
    time for connect:     1.57ms      2.72ms      1.83ms       289us    81.25%
    time to 1st byte:    33.32ms    174.93ms     92.64ms     41.15ms    62.50%
    req/s           :       9.35       15.04       11.29        2.12    75.00%


    finished in 5.31s, 564.53 req/s, 2.68MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 14.26MB (14949000) total, 281.25KB (288000) headers (space savings 0.00%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:     9.80ms    230.00ms     87.52ms     30.51ms    72.73%
    time for connect:     1.66ms      2.88ms      1.98ms       332us    81.25%
    time to 1st byte:    33.02ms    147.05ms     71.40ms     29.21ms    68.75%
    req/s           :       8.73       15.01       11.91        2.32    48.44%



Skitai + Atila I with HTTP/2.0
``````````````````````````````````````

.. code:: python

    ./run-skitai-atila.py
    # URI: /bench2

.. code:: bash

    finished in 4.27s, 702.36 req/s, 3.27MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.96MB (14637133) total, 22.75KB (23293) headers (space savings 92.68%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:    32.53ms    332.15ms    169.49ms     36.94ms    76.00%
    time for connect:     1.73ms      2.84ms      2.01ms       267us    79.69%
    time to 1st byte:    53.09ms    199.33ms    118.25ms     45.64ms    56.25%
    req/s           :      10.83       12.82       11.72        0.62    57.81%


    finished in 4.15s, 723.38 req/s, 3.37MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.96MB (14637179) total, 22.79KB (23339) headers (space savings 92.66%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:    35.29ms    279.69ms    155.73ms     30.95ms    70.67%
    time for connect:     1.59ms      2.71ms      1.88ms       271us    78.13%
    time to 1st byte:    50.17ms    253.40ms    127.24ms     55.61ms    62.50%
    req/s           :      11.12       15.66       12.94        1.73    68.75%


    finished in 4.66s, 644.41 req/s, 3.00MB/s
    requests: 3000 total, 3000 started, 3000 done, 3000 succeeded, 0 failed, 0 errored, 0 timeout
    status codes: 3000 2xx, 0 3xx, 0 4xx, 0 5xx
    traffic: 13.96MB (14637984) total, 23.58KB (24144) headers (space savings 92.41%), 13.88MB (14556000) data
                        min         max         mean         sd        +/- sd
    time for request:    47.83ms    328.79ms    166.56ms     40.65ms    72.77%
    time for connect:     1.70ms      2.76ms      1.97ms       255us    78.13%
    time to 1st byte:    49.62ms    282.23ms    143.07ms     59.23ms    62.50%
    req/s           :       9.92       14.76       12.08        1.48    48.44%


