import asyncio
from rs4 import asynchat

async def transit (request, protocol_class, loop = None, args = (), kwargs = {}):
    request.channel.del_channel ()
    current_loop = loop or asyncio.get_event_loop ()
    transport, protocol = await current_loop.create_connection (
        lambda: protocol_class (request, *args, **kwargs),
        sock = request.channel.conn
    )
    return protocol


class aiochat (asyncio.Protocol, asynchat.async_chat):
    use_encoding = 0
    def __init__(self, request):
        self.request = request
        self.ac_in_buffer = b''
        self._closed = False

    def __aiter__ (self):
        return self

    async def __anext__ (self):
        item = await self.receive ()
        if item is None:
            raise StopAsyncIteration
        return item

    async def receive (self):
        return await self.request.collector.get ()

    def push (self, data):
        self.log_bytes_out (data)
        self.transport.write (data)

    def close (self):
        if self._closed:
            return
        self.request.channel and self.request.channel.close ()
        self.transport.close ()
        self.request.collector.ch = self.request.collector.channel = None
        self._closed = True

    def log_bytes_out (self, data):
        lr = len (data)
        self.request.channel.server.bytes_out.inc (lr)
        self.request.channel.bytes_out.inc (lr)

    def log_bytes_in (self, data):
        lr = len (data)
        self.request.channel.server.bytes_in.inc (lr)
        self.request.channel.bytes_in.inc (lr)

    def found_terminator(self):
        self.request.collector.found_terminator()

    def collect_incoming_data(self, data):
        self.request.collector.collect_incoming_data(data)

    def data_received (self, data):
        self.log_bytes_in (data)
        self.find_terminator (data)

    def connection_made (self, transport):
        self.transport = transport
        self.handle_connect ()

    def connection_lost (self, exc):
        self.handle_close ()
        self.close ()

    def handle_close (self):
        self.request.collector.close ()

    def handle_connect (self, data):
        pass
