import os
from aquests.lib import pathtool

DEFAULT = """[smtpda]
# SMTP Delivery Agent
max-retry = 10
keep-days = 1
smtp-server =
user =
password =
ssl = true
"""

_default_conf = os.path.join (os.environ ["HOME"], ".skitai.conf")
_default_log_dir = "/var/log/skitai"
_default_var_dir = "/var/tmp/skitai"

pathtool.mkdir (_default_log_dir)
pathtool.mkdir (_default_var_dir)
