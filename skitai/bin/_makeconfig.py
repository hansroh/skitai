import os

DEFAULT = """[common]
log-path =

[smtpda]
# SMTP Delivery Agent
max-retry = 10
keep-days = 1
smtp-server =
user =
password =
ssl = true

[:crontab]
# Example: 0/5 * * * * /usr/bin/python3 something


"""


_default_conf = os.path.join (os.environ ["HOME"], ".skitai.conf")
if not os.path.exists (_default_conf):
    with open (_default_conf, "w") as f:
        f.write (DEFAULT)
