from aioquic.h3.connection import H3Connection
from aioquic.h3.connection import encode_frame, encode_uint_var
try:
    from aioquic.h3.connection import parse_uint_var
except ImportError:
    from aioquic.h3.connection import parse_max_push_id as parse_uint_var
from aioquic.h3.connection import FrameType, StreamType, FrameUnexpected
from aioquic.h3.exceptions import NoAvailablePushIDError
from .events import PushCanceled, MaxPushIdReceived, ConnectionShutdownInitiated
from rs4.annotations import override

class H3Connection (H3Connection):
    def __init__ (self, quic):
        super ().__init__ (quic)
        self._max_client_bidi_stream_id = 0 if not self._is_client else None
        self._push_map = {}
        self._canceled_push_ids = set ()
        self._uncaught_events = []

    @override
    def send_push_promise (self, stream_id, headers):
        push_stream_id = super ().send_push_promise (stream_id, headers)
        self._push_map [push_stream_id] = self._next_push_id - 1
        return push_stream_id

    def get_push_id (self, stream_id):
        try:
            return self._push_map [stream_id]
        except KeyError:
            raise AssertionError("No such stream ID")

    def cancel_push (self, push_id):
        self._canceled_push_ids.add (push_id)
        self._quic.send_stream_data (self._local_control_stream_id, encode_frame(FrameType.CANCEL_PUSH, encode_uint_var(push_id)))

    def shutdown (self, last_stream_id = None):
        assert not self._is_client, "Client must not send a goaway frame"
        if last_stream_id is None:
            last_stream_id = self._max_client_bidi_stream_id

        else:
            if last_stream_id == -1:
                last_stream_id = -4
            assert last_stream_id % 4 == 0 and (-4 <= last_stream_id <= self._max_client_bidi_stream_id), "Unissued request stream"

        frame = encode_frame(FrameType.GOAWAY, encode_uint_var(last_stream_id + 4))
        self._quic.send_stream_data (self._local_control_stream_id, frame)

    @override
    def handle_event (self, event):
        http_events = super ().handle_event (event)
        _uncaught_events, self._uncaught_events = self._uncaught_events, []
        return http_events + _uncaught_events

    @override
    def _handle_control_frame (self, frame_type, frame_data):
        http_events = super ()._handle_control_frame (frame_type, frame_data)
        assert http_events is None, '_handle_control_frame() returns something, update this method'

        if frame_type == FrameType.MAX_PUSH_ID:
            self._uncaught_events.append (MaxPushIdReceived (push_id = self._max_push_id))

        elif frame_type == FrameType.CANCEL_PUSH:
            _push_id = parse_uint_var (frame_data)
            self._canceled_push_ids.add (_push_id)
            self._uncaught_events.append (PushCanceled (push_id = _push_id))

        elif frame_type == FrameType.GOAWAY:
            _last_stream_id = max (-1, parse_uint_var (frame_data) - 4)
            self._uncaught_events.append (ConnectionShutdownInitiated (last_stream_id = _last_stream_id))

    @override
    def _handle_request_or_push_frame (self, frame_type, frame_data, stream, stream_ended):
        if frame_type == FrameType.HEADERS:
            if not self._is_client and stream.push_id is None:
                self._max_client_bidi_stream_id = max (stream.stream_id, self._max_client_bidi_stream_id)
        return super ()._handle_request_or_push_frame (frame_type, frame_data, stream, stream_ended)