import pytest

def test_launch (launch):
    with launch ("./examples/app_primitive.py") as engine:
        resp = engine.get ("/")
        assert resp.text == "Hello Atila"
