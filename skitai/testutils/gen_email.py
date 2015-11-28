from skitai.protocol.smtp import composer, async_smtp
from skitai.lib import logger
from skitai import lifetime

log = logger.screen_logger ()
composer.Composer.SAVE_PATH = r"C:\skitaid\var\daemons\smtpda\mail\spool"

"""
m = composer.Composer ("GAMIL SMTP TEST", "eunheemax@gmail.com", "hansroh@gmail.com")
m.set_smtp ("smtp.gmail.com:465", "eunheemax@gmail.com", "!kms2000", True)
m.add_text ("Hello World<div><img src='cid:A'></div>", "text/html")
m.add_attachment (r"D:\itunes-incoming-ebook\picpick\001.png", cid="A")
m.send ()

"""	
m = composer.Composer ("LUFEX SMTP TEST", "technical@lufex.com", "hansroh@gmail.com")
m.set_smtp ("mail.lufex.com:25", "technical", "whddlgkr", False)
m.add_text ("Hello World<div><img src='cid:A'></div>", "text/html")
m.add_attachment (r"D:\itunes-incoming-ebook\picpick\001.png", cid="A")
m.send ()
