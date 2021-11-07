from skitai.concurrent import aquests
from rs4.protocols import dns
from rs4 import asyncore
from rs4 import logger

def assert_status (resp):
    global ERRS
    if resp.status_code != resp.meta.get ("expect", 200):
        rprint (resp.status_code)
        ERRS += 1

def test_dns_error ():
    ERRS = 0
    aquests.configure (1, callback = assert_status, force_http1 = 1)
    [ aquests.get ("http://sdfiusdoiksdflsdkfjslfjlsf.com", meta = {"expect": 704}) for i in range (2) ]
    aquests.fetchall ()

    assert ERRS == 0

def _print (ans):
    assert ans
    if ans[0]['name'] == "www.allrightsales.com":
        assert ans[0]['status'] == "NXDOMAIN"
    else:
        assert ans[-1]['data']
        print (ans[0]['name'], ans[-1]['data'])

def loop ():
    dns.pop_all ()
    while asyncore.socket_map:
        dns.pop_all ()
        asyncore.loop (timeout = 1, count = 1)
        if not sum ([isinstance (r, dns.TCPClient) for r in asyncore.socket_map.values ()]):
            break

def test_adns ():
    dns.create_pool ([], logger.screen_logger ())
    for p in ("udp", "tcp"):
        dns.query ("www.microsoft.com", protocol = p, callback = _print, qtype="a")
        dns.query ("www.cnn.com", protocol = p, callback = _print, qtype="a")
        dns.query ("www.gitlab.com", protocol = p, callback = _print, qtype="a")
        dns.query ("www.alexa.com", protocol = p, callback = _print, qtype="a")
        dns.query ("www.yahoo.com", protocol = p, callback = _print, qtype="a")
        dns.query ("www.github.com", protocol = p, callback = _print, qtype="a")
        dns.query ("www.google.com", protocol = p, callback = _print, qtype="a")
        dns.query ("www.amazon.com", protocol = p, callback = _print, qtype="a")
        dns.query ("www.almec.com", protocol = p, callback = _print, qtype="a")
        dns.query ("www.alamobeauty.com", protocol = p, callback = _print, qtype="a")
        dns.query ("www.alphaworld.com", protocol = p, callback = _print, qtype="a")
        dns.query ("www.allrightsales.com", protocol = p, callback = _print, qtype="a")
        dns.query ("www.glasteel.com", protocol = p, callback = _print, qtype="a")

    loop ()
