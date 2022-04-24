
from rs4.webkit.pools import RequestPool

def test_request_pool ():
    p = RequestPool (10)
    with p.acquire () as s:
        r = s.get ("http://example.com")
        assert r.status_code == 200