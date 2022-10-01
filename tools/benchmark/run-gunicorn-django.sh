cd bench
gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 4 bench.wsgi



