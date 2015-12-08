from skitai.lib import logger
from skitai.protocol.dns import asyndns
import asyncore

import pprint
f = asyndns.Request (logger.screen_logger ())
f.req ("google.com", protocol = "tcp", callback = pprint.pprint, qtype="mx")
f.req ("www.google.com", protocol = "tcp", callback = pprint.pprint, qtype="a")
f.req ("www.google.com", protocol = "tcp", callback = pprint.pprint, qtype="ns")
asyncore.loop (timeout = 1)
