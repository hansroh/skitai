Benchmark Code
=========================

May 23, 2020

.. code:: bash

    export MYDB="user:passwd@192.168.0.80/bench"
    ./install.sh

- Django Dev Server
- Uvicorn + Django ASGI
- Gunicorn + Django WSGI
- Skitai + Django WSGI
- Skitai + Atila I WSGI
- Skitai + Atila II WSGI


Benchmark Tool and Command
==============================

.. code:: bash

    h2load --h1 -n3000 -c64 -t4 http://192.168.0.100:9019/bench

    # HTTP/2.0
    h2load -m2 -n3000 -c64 -t4 http://192.168.0.154:9007/bench


Benchmark Result (3 Runs Each)
======================================

Django Dev Server
-------------------------

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


Gunicorn + Django WSGI
---------------------------

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
------------------------

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
------------------------

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


Skitai + Django
----------------------

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
------------------

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
------------------

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
------------------

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
---------------------------------------------

.. code:: python

     ./run-skitai-atila.py

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



Skitai + Atila II
---------------------------------------------

.. code:: python

    ./run-skitai-atila.py
    # URI: /bench2

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




Skitai + Atila II with HTTP/2.0
----------------------------------------

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





