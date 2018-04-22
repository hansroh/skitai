"""
2015. 12. 10
Hans Roh
"""
from .Saddle import Saddle

# Events
app_starting = "app:starting"
app_started = "app:started"
app_restarting = "app:restarting"
app_restarted = "app:restarted"
app_mounted = "app:mounted"
app_unmounting = "app:umounting"

request_failed = "request:failed"
request_success = "request:success"
request_tearing_down = "request:teardown"
request_starting = "request:started"
request_finished = "request:finished"

template_rendering = "template:rendering"
template_rendered = "template:rendered"

