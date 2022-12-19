from ...backbone import aiochat
from rs4.protocols.sock.impl.ws import collector, OPCODE_TEXT, OPCODE_BINARY

class WebSocketProtocol (aiochat.aiochat):
    def __init__ (self, request, keep_alive):
        super ().__init__ (request)
        self.keep_alive = keep_alive
        self.channel = request.channel
        self.collector = request.collector
        self.out_bytes = 0

    def handle_connect (self):
        self.collector.set_channel (self)
        self.request.response.set_reply ("101 Web Socket Protocol Handshake")
        self.push (self.request.response.build_reply_header ().encode ())

    async def send (self, data):
        data = collector.encode_message (data, OPCODE_TEXT if isinstance (data, str) else OPCODE_BINARY)
        self.out_bytes += len (data)
        self.push (data)
