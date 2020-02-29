
import sys
import time

QUICK_ENABLED = False

if sys.version_info >= (3, 6):
    QUICK_ENABLED = True

    from skitai.backbone import http3_server
    import ssl
    from aioquic.quic import events
    from aioquic.h3 import connection as h3
    from aioquic.h3.events import DataReceived, HeadersReceived, H3Event
    from aioquic.h3.exceptions import H3Error, NoAvailablePushIDError
    from aioquic.buffer import Buffer
    from aioquic.quic.packet import (
        PACKET_TYPE_INITIAL,
        encode_quic_retry,
        encode_quic_version_negotiation,
        pull_quic_header
    )
    from aioquic.quic.retry import QuicRetryTokenHandler
    from aioquic.quic.connection import QuicConnection
    from aioquic.h3.connection import H3_ALPN
    from aioquic.quic.configuration import QuicConfiguration
    from quicutil.utils import SERVER_CACERTFILE, SERVER_CERTFILE, SERVER_KEYFILE

    CLIENT_ADDR = ("1.2.3.4", 1234)
    SERVER_ADDR = ("2.3.4.5", 4433)

#----------------------------------------------------
def make_connection ():
    server_configuration = QuicConfiguration(is_client=False)
    server_configuration.load_cert_chain(SERVER_CERTFILE, SERVER_KEYFILE)
    quic = QuicConnection(configuration=server_configuration)
    quic._ack_delay = 0
    return h3.H3Connection (quic)

def make_client ():
    client_configuration = QuicConfiguration(is_client=True)
    client_configuration.load_verify_locations(cafile=SERVER_CACERTFILE)
    client = QuicConnection(configuration=client_configuration)
    client._ack_delay = 0
    return client

def datagram_sizes(items):
    return [len(x[0]) for x in items]

# test ----------------------------------------------------
def test_tls ():
    if not QUICK_ENABLED: return

    ctx = http3_server.init_context (
        './examples/resources/certifications/server.crt',
        './examples/resources/certifications/server.key',
        "fatalbug"
    )
    print (ctx.alpn_protocols)
    assert 'h3-25' in ctx.alpn_protocols
    assert ctx.verify_mode == ssl.VerifyMode.CERT_NONE

def test_quic_compatibility ():
    if not QUICK_ENABLED: return

    now = 0.0
    client = make_client ()
    client.connect(SERVER_ADDR, now=now)
    items = client.datagrams_to_send(now=now)
    assert datagram_sizes(items) == [1280]
    assert client.get_timer() == 1.0

    conn = make_connection ()
    quic = conn._quic
    now = 1.1
    quic.receive_datagram(items[0][0], CLIENT_ADDR, now=now)
    items = quic.datagrams_to_send(now=now)
    a, b = datagram_sizes(items)
    assert a == 1280
    assert b in (1084,1062) # passed in 0.8.6

    assert quic.get_timer() == 2.1
    quic.handle_timer (now)

    for func in (
        'handle_timer',
        'next_event',
        'close',
        'send_ping'
    ):
        assert hasattr (quic, func)

    for func in (
        'handle_event',
        'send_push_promise'
    ):
        assert hasattr (conn, func)

    quic.close (error_code=0, frame_type = h3.FrameType.GOAWAY, reason_phrase='null')

