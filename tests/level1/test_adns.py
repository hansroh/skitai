import aquests

def assert_status (resp):
    global ERRS
    if resp.status_code != resp.meta.get ("expect", 200):
        rprint (resp.status_code)
        ERRS += 1        
        
def test_dns_error ():
    ERRS = 0
    aquests.configure (1, callback = assert_status, force_http1 = 1)    
    [ aquests.get ("http://sdfiusdoiksdflsdkfjslfjlsf.com", meta = {"expect": 704}) for i in range (3) ]
    aquests.fetchall ()

    assert ERRS == 0