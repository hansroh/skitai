import pytest
import requests
    
def test_proxy (launch):
    proxies = {
        'http': 'http://127.0.0.1:30371',
        'https': 'http://127.0.0.1:30371',
    }
    with launch ("./examples/proxy.py") as engine:
        resp = requests.get ("http://example.com/", proxies = proxies)
        assert resp.status_code == 200
        assert "Example Domain" in resp.text
        
        resp = requests.get ("https://pypi.org/project/rs4/", proxies = proxies)
        assert resp.status_code == 200
        assert "Project description" in resp.text
