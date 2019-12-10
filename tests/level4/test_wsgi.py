def test_wsgi (launch):
    with launch ("./examples/wsgi-basic.py") as engine:
        resp = engine.get ("/")
        assert resp.status_code == 200
        assert "Hello World" in resp.text

def test_wsgi_atila (launch):
    with launch ("./examples/wsgi-atila.py") as engine:
        resp = engine.get ("/")
        assert resp.status_code == 200
        assert "Hello Atila" in resp.text

def test_wsgi_multi (launch):
    with launch ("./examples/wsgi-multi.py") as engine:
        resp = engine.get ("/")
        assert resp.status_code == 200
        assert "Hello World" in resp.text

        resp = engine.get ("/atila")
        assert resp.status_code == 200
        assert "Hello Atila" in resp.text
