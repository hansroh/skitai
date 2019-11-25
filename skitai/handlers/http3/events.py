from aioquic.h3.events import H3Event, DataReceived, HeadersReceived
from dataclasses import dataclass

@dataclass
class PushCanceled (H3Event):
    push_id: int

@dataclass
class MaxPushIdReceived (H3Event):
    push_id: int
