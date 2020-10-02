import skitai
import confutil
import pprint
import re
import os
import requests
import pytest
from requests.exceptions import ConnectionError

def test_upload (launch):    
    with launch ("./examples/app.py") as cli:		
        for size in (4096, 4096000, 40960000):
            with open ('./examples/statics/{}.htm'.format (size), 'wb') as f:
                f.write (b'x' * size)  

            if size == 40960000:
                with pytest.raises (ConnectionError):
                    resp = requests.post ('http://127.0.0.1:30371/upload2', {'aaaa': '1234'}, files = {'ffff': open ('./examples/statics/{}.htm'.format (size), "rb") })
            else:    
                resp = requests.post ('http://127.0.0.1:30371/upload2', {'aaaa': '1234'}, files = {'ffff': open ('./examples/statics/{}.htm'.format (size), "rb") })
                assert resp.status_code == 200
            assert 'aaaa' in resp.text
            assert 'ffff' in resp.text
            os.remove ('./examples/statics/{}.htm'.format (size))
        
    