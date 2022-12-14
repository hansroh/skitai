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


class ChatProtocol (asyncio.Protocol):
    use_encoding = 0
    def __init__(self, request):
        self.request = request
        self.ac_in_buffer = b''

    def __aiter__ (self):
        return self.request.collector

    async def __anext__ (self):
        return await self.recive ()

    async def recive (self):
        return await self.request.collector.mq.get ()

    def handle_close (self, data):
        pass

    def handle_connect (self, data):
        pass

    def push (self, data):
        self.log_bytes_out (data)
        self.transport.write (data)

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
        self.request.collector.mq.put_nowait (None)
        self.request.channel and self.request.channel.close ()
        self.handle_close ()

    def set_terminator(self, term):
        if isinstance(term, str) and self.use_encoding:
            term = bytes(term, self.encoding)
        elif isinstance(term, int) and term < 0:
            raise ValueError('the number of received bytes must be positive')
        self.terminator = term

    def get_terminator(self):
        return self.terminator

    def find_terminator (self, data):
        if isinstance(data, str) and self.use_encoding:
            data = bytes(str, self.encoding)
        self.ac_in_buffer = self.ac_in_buffer + data

        while self.ac_in_buffer:
            lb = len(self.ac_in_buffer)
            terminator = self.get_terminator()
            if not terminator:
                # no terminator, collect it all
                self.collect_incoming_data(self.ac_in_buffer)
                self.ac_in_buffer = b''
            elif isinstance(terminator, int):
                # numeric terminator
                n = terminator
                if lb < n:
                    self.collect_incoming_data(self.ac_in_buffer)
                    self.ac_in_buffer = b''
                    self.terminator = self.terminator - lb
                else:
                    self.collect_incoming_data(self.ac_in_buffer[:n])
                    self.ac_in_buffer = self.ac_in_buffer[n:]
                    self.terminator = 0
                    self.found_terminator()
            else:
                terminator_len = len(terminator)
                index = self.ac_in_buffer.find(terminator)
                if index != -1:
                    if index > 0:
                        self.collect_incoming_data(self.ac_in_buffer[:index])
                    self.ac_in_buffer = self.ac_in_buffer[index+terminator_len:]
                    self.found_terminator()
                else:
                    index = asynchat.find_prefix_at_end(self.ac_in_buffer, terminator)
                    if index:
                        if index != lb:
                            self.collect_incoming_data(self.ac_in_buffer[:-index])
                            self.ac_in_buffer = self.ac_in_buffer[-index:]
                        break
                    else:
                        self.collect_incoming_data(self.ac_in_buffer)
                        self.ac_in_buffer = b''
