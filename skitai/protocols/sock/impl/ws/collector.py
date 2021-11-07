import sys
import struct
from rs4.misc import strutil
from io import BytesIO
from ..ws import *

def encode_message (message, op_code):
    header  = bytearray()
    if op_code != OPCODE_BINARY and strutil.is_encodable (message):
        payload = message.encode ("utf8")
    else:
        payload = message
    payload_length = len(payload)

    # Normal payload
    if payload_length <= 125:
        header.append(FIN | op_code)
        header.append(payload_length)

    # Extended payload
    elif payload_length >= 126 and payload_length <= 65535:
        header.append(FIN | op_code)
        header.append(PAYLOAD_LEN_EXT16)
        header.extend(struct.pack(">H", payload_length))

    # Huge extended payload
    elif payload_length < 18446744073709551616:
        header.append(FIN | op_code)
        header.append(PAYLOAD_LEN_EXT64)
        header.extend(struct.pack(">Q", payload_length))

    else:
        raise AssertionError ("Message is too big. Consider breaking it into chunks.")
    return header + payload


class Collector:
    def __init__ (self, message_encoding = None):
        self.rfile = BytesIO ()
        self.masks = b""
        self.has_masks = True
        self.buf = b""
        self.payload_length = 0
        self.opcode = None
        self.default_op_code = OPCODE_TEXT

    def _tobytes (self, b):
        if sys.version_info[0] < 3:
            return map(ord, b)
        else:
            return b

    def collect_incoming_data (self, data):
        #print (">>>>", data)
        if not data:
            # closed connection
            self.close ()
            return

        if self.masks or (not self.has_masks and self.payload_length):
            self.rfile.write (data)
        else:
            self.buf += data

    def found_terminator (self):
        buf, self.buf = self.buf, b""
        if self.masks or (not self.has_masks and self.payload_length):
            # end of message
            masked_data = bytearray(self.rfile.getvalue ())
            if self.masks:
                masking_key = bytearray(self.masks)
                data = bytearray ([masked_data[i] ^ masking_key [i%4] for i in range (len (masked_data))])
            else:
                data = masked_data

            if self.opcode == OPCODE_TEXT:
                # text
                data = data.decode('utf-8')
            opcode = self.opcode

            self.payload_length = 0
            self.opcode = None
            self.masks = b""
            self.has_masks = True
            self.rfile.seek (0)
            self.rfile.truncate ()
            self.channel.set_terminator (2)

            if opcode == OPCODE_PONG:
                pass
            elif opcode == OPCODE_PING:
                self.channel.push (encode_message (data, OPCODE_PONG))
            elif opcode == OPCODE_CLOSE:
                self.close ()
            else:
                self.handle_message (data)

        elif self.payload_length:
            self.masks = buf
            self.channel.set_terminator (self.payload_length)

        elif self.opcode:
            if len (buf) == 2:
                fmt = ">H"
            else:
                fmt = ">Q"
            self.payload_length = struct.unpack(fmt, self._tobytes(buf))[0]
            if self.has_masks:
                self.channel.set_terminator (4) # mask
            else:
                self.channel.set_terminator (self.payload_length)

        elif self.opcode is None:
            b1, b2 = self._tobytes(buf)
            fin    = b1 & FIN
            self.opcode = b1 & OPCODE
            mask = b2 & MASKED
            if not mask:
                self.has_masks = False

            payload_length = b2 & PAYLOAD_LEN
            if payload_length == 0:
                self.opcode = None
                self.has_masks = True
                self.channel.set_terminator (2)
                return

            if payload_length < 126:
                self.payload_length = payload_length
                if self.has_masks:
                    self.channel.set_terminator (4) # mask
                else:
                    self.channel.set_terminator (self.payload_length)
            elif payload_length == 126:
                self.channel.set_terminator (2)    # short length
            elif payload_length == 127:
                self.channel.set_terminator (8) # long length

        else:
            raise AssertionError ("Web socket frame decode error")

    def handle_message (self, msg):
        raise NotImplementedError ("handle_message () not implemented")
