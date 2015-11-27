from skitai.protocol.smtp import composer, async_smtp
from skitai.lib import logger
from skitai import lifetime

log = logger.screen_logger ()
"""
m = composer.Composer ("GAMIL SMTP TEST", "eunheemax@gmail.com", "hansroh@gmail.com")
m.set_smtp ("smtp.gmail.com:465", "eunheemax@gmail.com", "!kms2000", True)
m.add_text ("Hello World<div><img src='cid:A'></div>", "text/html")
m.add_attachment (r"D:\itunes-incoming-ebook\picpick\001.png", cid="A")
async_smtp.SMTP_SSL (m, log)
"""	

m = composer.Composer ("LUFEX SMTP TEST", "technical@lufex.com", "hansroh@gmail.com")
m.set_smtp ("mail.lufex.com", "technical", "whddlgkr", True)
m.add_text ("Hello World<div><img src='cid:A'></div>", "text/html")
m.add_attachment (r"D:\itunes-incoming-ebook\picpick\001.png", cid="A")
async_smtp.SMTP (m, log)

lifetime.loop ()
