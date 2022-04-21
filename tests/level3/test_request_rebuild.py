from rs4.protocols.builder import make_http

def test_make_http ():
    # method, url, params, auth, headers, meta, proxy, logger
    req = make_http ("get", "/index", None, None, [], None, None, None)
    assert req.headers ["accept"] == "*/*"

    req = make_http ("get", "/index", {"a": "b"}, None, [], None, None, None)
    assert req.headers ["accept"] == "*/*"
    assert req.get_payload () == b""

    req = make_http ("post", "/index", {"a": "b"}, None, [], None, None, None)
    assert req.headers ["accept"] == "*/*"
    assert req.headers ["content-type"] == "application/x-www-form-urlencoded; charset=utf-8"
    assert req.get_payload () == b"a=b"

    req = make_http ("post", "/index", {"a": "b"}, None, {"Accept": "text/html"}, None, None, None)
    assert req.headers ["accept"] == "text/html"
    assert req.headers ["content-type"] == "application/x-www-form-urlencoded; charset=utf-8"

    req = make_http ("postjson", "/index", {"a": "b"}, None, {"Accept": "text/html"}, None, None, None)
    assert req.headers ["accept"] == "text/html"
    assert req.headers ["content-type"] == "application/json; charset=utf-8"

    req = make_http ("post", "/index", "a=b", None, {"Accept": "text/html", "Content-Type": "application/test"}, None, None, None)
    assert req.headers ["accept"] == "text/html"
    assert req.headers ["content-type"] == "application/test"

    req = make_http ("postjson", "/index", {"a": "b"}, None, None, None, None, None)
    assert req.headers ["accept"] == "application/json"
    assert req.headers ["content-type"] == "application/json; charset=utf-8"
