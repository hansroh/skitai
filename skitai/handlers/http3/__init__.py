from aioquic.buffer import Buffer
from aioquic.quic.packet import (
    PACKET_TYPE_INITIAL,
    encode_quic_retry,
    encode_quic_version_negotiation,
    pull_quic_header,
)
from aioquic.quic.retry import QuicRetryTokenHandler
from aioquic.quic.connection import QuicConnection
import os

def QUIC (channel, data, stateless_retry = False):
    ctx = channel.server.ctx
    _retry = QuicRetryTokenHandler() if stateless_retry else None

    buf = Buffer (data=data)
    header = pull_quic_header (
        buf, host_cid_length = ctx.connection_id_length
    )
    # version negotiation
    if header.version is not None and header.version not in ctx.supported_versions:
        self.channel.push (
            encode_quic_version_negotiation (
                source_cid = header.destination_cid,
                destination_cid = header.source_cid,
                supported_versions = ctx.supported_versions,
            )
        )
        aa
        return

    assert len (data) >= 1200
    assert header.packet_type == PACKET_TYPE_INITIAL
    original_connection_id = None
    if _retry is not None:
        if not header.token:
            # create a retry token
            channel.push (
                encode_quic_retry (
                    version = header.version,
                    source_cid = os.urandom(8),
                    destination_cid = header.source_cid,
                    original_destination_cid = header.destination_cid,
                    retry_token = _retry.create_token (channel.addr, header.destination_cid),
                )
            )
            return

        else:
            try:
                original_connection_id = _retry.validate_token (
                    channel.addr, header.token
                )
            except ValueError:
                return

    # create new connection
    return QuicConnection (
        configuration = ctx,
        logger_connection_id = original_connection_id or header.destination_cid,
        original_connection_id = original_connection_id,
        session_ticket_fetcher = channel.server.ticket_store.pop,
        session_ticket_handler = channel.server.ticket_store.add
    )
