from wsproto import WSConnection, ConnectionType
from wsproto.events import AcceptConnection, Request, CloseConnection, Ping, TextMessage, BytesMessage
from wsproto.utilities import RemoteProtocolError
import asyncio

class WebSocketProtocolWSProto (asyncio.Protocol):
    def __init__ (self, request, keep_alive):
        self.request = request
        self.keep_alive = keep_alive
        self.channel = request.channel
        self.text = ''
        self.bytes = ''
        self.mq = asyncio.Queue ()
        self.data_to_send = []
        self.conn = None
        self.loop = asyncio.get_event_loop ()

    def __aiter__ (self):
        return self

    async def __anext__ (self):
        return await self.mq.get ()

    def connection_made (self, transport):
        self.transport = transport
        self.conn = WSConnection (ConnectionType.SERVER)
        req = self.request.request + '\r\n' + "\r\n".join (self.request.header) + '\r\n\r\n'
        self.conn.receive_data (req.encode ())
        self.handle_events ()

    def data_received (self, data):
        lr = len (data)
        self.channel.server.bytes_in.inc (lr)
        self.channel.bytes_in.inc (lr)
        try:
            self.conn.receive_data (data)
        except RemoteProtocolError as err:
            self._send (self.conn.send (err.event_hint))
            self.close ()
        else:
            self.handle_events ()

    def connection_lost (self, exc):
        self.loop.call_soon_threadsafe (self.mq.put_nowait, None)

    def _send (self):
        if not self.data_to_send:
            return
        data_to_send, self.data_to_send = self.data_to_send, []
        data = b''.join (data_to_send)
        lr = len (data)
        self.channel.server.bytes_out.inc (lr)
        self.channel.bytes_out.inc (lr)
        self.transport.write (data)

    async def send (self, data, end_data = True):
        event = TextMessage if isinstance (data, str) else BytesMessage
        data = self.conn.send (event (data))
        self.data_to_send.append (data)
        self._send ()

    async def receive (self):
        return await self.mq.get ()

    def close (self):
        self.transport.close ()
        self.request.channel and self.request.channel.close ()

    def handle_events (self):
        for event in self.conn.events ():
            if isinstance(event, Request):
                self.handle_connect (event)
            elif isinstance (event, TextMessage):
                self.handle_text (event)
            elif isinstance (event, BytesMessage):
                self.handle_bytes (event)
            elif isinstance (event, CloseConnection):
                self.handle_close (event)
            elif isinstance (event, Ping):
                self.handle_ping (event)
        self._send ()

    def handle_text (self, event):
        self.text += event.data
        if event.message_finished:
            _, self.text = self.text, ''
            self.loop.call_soon_threadsafe (self.mq.put_nowait, _)

    def handle_bytes (self, event):
        self.bytes += event.data
        if event.message_finished:
            _, self.bytes = self.bytes, b''
            self.loop.call_soon_threadsafe (self.mq.put_nowait, _)

    def handle_close (self, event):
        data = self.conn.send (event.response ())
        self.data_to_send.append (data)
        self.close ()

    def handle_connect (self, event):
        data = self.conn.send (AcceptConnection ())
        self.data_to_send.append (data)

    def handle_ping (self, event):
        data = self.conn.send (event.response ())
        self.data_to_send.append (data)
