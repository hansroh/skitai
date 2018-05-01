import os
from skitai.server.wastuff import process, daemon    
from aquests.lib import pathtool

DEFAULT = """[smtpda]
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
    with open (_default_conf + ".example", "w") as f:
        f.write (DEFAULT)    
    _default_log_dir = daemon.get_default_logpath ()
    _default_var_dir = daemon.get_default_varpath ()
    
else:
    _default_log_dir = "/var/log/skitai/default"
    _default_var_dir = "/var/tmp/skitai/default"

pathtool.mkdir (_default_log_dir)
pathtool.mkdir (_default_var_dir)
