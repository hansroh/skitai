echo staring tests/examples/app.py ...

python3 tests/examples/app.py -d

echo ================================================
echo HTTP/1.1 -n3000 -c1000 6b
echo ================================================
h2load -n3000 -c1000 --h1 http://127.0.0.1:30371/hello?num=1

echo ================================================
echo HTTP/1.1 -n3000 -c1000 6kb
echo ================================================
h2load -n3000 -c1000 --h1 http://127.0.0.1:30371/hello?num=1000

echo ================================================
echo HTTP/2 -n3000 -c1000 -m2 6b
echo ================================================
h2load -n3000 -c1000 -m2 http://127.0.0.1:30371/hello?num=1

echo ================================================
echo HTTP/2 -n3000 -c1000 -m2 6kb
echo ================================================
h2load -n3000 -c1000 -m2 http://127.0.0.1:30371/hello?num=1000

echo ================================================
echo HTTP/2 -n3000 -c1000 -m1 6kb
echo ================================================
h2load -n3000 -c1000 -m1 http://127.0.0.1:30371/hello?num=1000

echo shutting down tests/examples/app.py ...
python3 tests/examples/app.py stop

echo benchmarking finished.

