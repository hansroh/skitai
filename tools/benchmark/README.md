# Benchmarking

*Updated at Oct 20, 2022*

## S/W Versions
### Tools
- h2load: nghttp2/1.12.0

### Python Libraries
- uvicorn==0.18.3
- fastapi==0.85.0
- atila==0.23.0
- skitai==0.53.0

## Command
```shell
h2load -n 10000 -c 1024 -t 20 --h1 http://skitai-dev:5000/bench
h2load -n 10000 -c 1024 -t 20 --h1 http://skitai-dev:5000/bench/async
```

Each result taken from 2nd run.







# Result

## Atila + Skitai
```shell
./run-skitai-atila.py > /dev/null
```

- `/bench`:
```
finished in 11.18s, 894.42 req/s, 4.33MB/s
requests: 10000 total, 10000 started, 10000 done, 10000 succeeded, 0 failed, 0 errored, 0 timeout
status codes: 10000 2xx, 0 3xx, 0 4xx, 0 5xx
traffic: 48.39MB (50740000) total, 937.50KB (960000) headers (space savings 0.00%), 47.14MB (49430000) data
                     min         max         mean         sd        +/- sd
time for request:    52.76ms       2.05s    954.53ms    285.38ms    76.15%
time for connect:      220us       1.03s    528.08ms    491.95ms    34.86%
time to 1st byte:    67.73ms       3.07s       1.28s    960.72ms    60.74%
req/s           :       0.82        1.26        1.00        0.10    64.26%
```

- `/bench/async`:
```
finished in 9.14s, 1093.67 req/s, 5.29MB/s
requests: 10000 total, 10000 started, 10000 done, 10000 succeeded, 0 failed, 0 errored, 0 timeout
status codes: 10000 2xx, 0 3xx, 0 4xx, 0 5xx
traffic: 48.39MB (50740000) total, 937.50KB (960000) headers (space savings 0.00%), 47.14MB (49430000) data
                     min         max         mean         sd        +/- sd
time for request:    15.03ms       3.00s    689.46ms    415.32ms    85.76%
time for connect:      245us       3.02s    723.73ms    951.31ms    87.99%
time to 1st byte:   125.57ms       5.88s       1.88s       1.76s    80.76%
req/s           :       1.01        1.71        1.33        0.18    57.62%
```

## FastAPI + Uvicorn
```shell
./run-uvicorn-fastapi.sh > /dev/null
```

- `/bench`:
```
finished in 15.98s, 625.88 req/s, 2.88MB/s
requests: 10000 total, 10000 started, 10000 done, 10000 succeeded, 0 failed, 0 errored, 0 timeout
status codes: 10000 2xx, 0 3xx, 0 4xx, 0 5xx
traffic: 46.04MB (48280000) total, 898.44KB (920000) headers (space savings 0.00%), 44.83MB (47010000) data
                     min         max         mean         sd        +/- sd
time for request:    10.88ms      15.57s    760.77ms       2.50s    92.45%
time for connect:      188us       1.02s    195.47ms    357.21ms    84.38%
time to 1st byte:    85.74ms      15.67s       7.02s       4.26s    58.50%
req/s           :       0.57       17.57        2.42        2.97    90.04%
```

- `/bench/async`:
```
finished in 9.44s, 1059.38 req/s, 4.88MB/s
requests: 10000 total, 10000 started, 10000 done, 10000 succeeded, 0 failed, 0 errored, 0 timeout
status codes: 10000 2xx, 0 3xx, 0 4xx, 0 5xx
traffic: 46.04MB (48280000) total, 898.44KB (920000) headers (space savings 0.00%), 44.83MB (47010000) data
                     min         max         mean         sd        +/- sd
time for request:     8.88ms       5.05s    819.00ms    423.76ms    75.18%
time for connect:      212us       1.03s    170.20ms    340.87ms    86.13%
time to 1st byte:    96.38ms       3.08s    792.96ms    585.11ms    73.83%
req/s           :       0.97        2.06        1.21        0.14    79.49%
```