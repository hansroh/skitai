from rs4 import webkit
import os

def test_selenium ():
    if not os.path.exists ("../../rs4"):
        return
    f = webkit.Site ("https://google.com")
    f.driver.get ("/")
    html = f.driver.html ()
    assert "www.google.com" in html

    f = webkit.Site ("https://google.com")
    with f.driver as d:
        d.get ("/")
        html = d.html ()
        assert "www.google.com" in html


