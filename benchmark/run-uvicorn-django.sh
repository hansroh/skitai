cd bench
uvicorn bench.asgi:application --host 0.0.0.0 --port 5000 --workers 4

