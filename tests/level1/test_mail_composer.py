from skitai.protocols.sock.impl.smtp import composer
import os
import pytest

def compose (m):
    data="""Hi,
I recieved your message today.

I promise your request is processed with very high priority.

Thanks.
    """
    m.add_content (data, "text/html", "utf8")
    m.add_attachment (os.path.join (os.path.dirname (__file__), "test_was.py"), cid="AAA")
    m.save ("./")

    assert m.H ["From"] == '"Tester"<hansroh@xxx.com>'
    assert m.H ["To"] == '"Hans Roh"<hansroh2@xxx.com>'
    assert m.H ["Subject"] == 'e-Mail Test'
    assert m.is_SSL ()
    assert m.get_FROM () == "hansroh@xxx.com"
    assert m.get_TO () == "hansroh2@xxx.com"
    assert m.get_SMTP () == ("smtp.gmail.com", 465)
    assert m.get_LOGIN () == ("ehmax@xxx.com", "password")
    assert os.path.basename (m.get_FILENAME ()).startswith ("0.")
    assert len (m.attachments) == 1

    composer.load (m.get_FILENAME ())
    assert m.get_DATA ().endswith ("--\r\n")
    assert "Content-ID: <AAA>" in m.get_DATA ()
    assert 'filename="test_was.py"' in m.get_DATA ()
    m.remove ()

def test_composer ():
    m = composer.Composer ("e-Mail Test", '"Tester"<hansroh@xxx.com>', '"Hans Roh"<hansroh2@xxx.com>')
    m.set_smtp ("smtp.gmail.com:465", "ehmax@xxx.com", "password", True)
    compose (m)

def test_composer_without_smtp ():
    m = composer.Composer ("e-Mail Test", '"Tester"<hansroh@xxx.com>', '"Hans Roh"<hansroh2@xxx.com>')
    with pytest.raises (AssertionError):
        compose (m)

def test_composer_with_default_smpt ():
    import skitai
    skitai.set_smtp ("smtp.gmail.com:465", "ehmax@xxx.com", "password", True, False)
    m = composer.Composer ("e-Mail Test", '"Tester"<hansroh@xxx.com>', '"Hans Roh"<hansroh2@xxx.com>')
    compose (m)

