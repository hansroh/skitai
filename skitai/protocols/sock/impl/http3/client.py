import argparse
import asyncio
import logging
import os
import pickle
import ssl
import time
from collections import deque
from typing import BinaryIO, Callable, Deque, Dict, List, Optional, Union, cast
from urllib.parse import urlparse
from urllib.parse import urlencode
from io import BytesIO
import wsproto
import wsproto.events
from rs4 import attrdict
import aioquic
from aioquic.asyncio.client import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h0.connection import H0_ALPN, H0Connection
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.h3.events import (
    DataReceived,
    H3Event,
    HeadersReceived,
    PushPromiseReceived,
)
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import QuicEvent
from aioquic.tls import CipherSuite, SessionTicket
from ..http2 import client as h2client

try:
    import uvloop
except ImportError:
    uvloop = None

logger = logging.getLogger("client")

HttpConnection = Union[H0Connection, H3Connection]

USER_AGENT = "aioquic/" + aioquic.__version__


class URL:
    def __init__(self, url: str) -> None:
        parsed = urlparse(url)

        self.authority = parsed.netloc
        self.full_path = parsed.path
        if parsed.query:
            self.full_path += "?" + parsed.query
        self.scheme = parsed.scheme


class HttpRequest:
    def __init__(
        self, method: str, url: URL, content: bytes = b"", headers: Dict = {}
    ) -> None:
        self.content = content
        self.headers = headers
        self.method = method
        self.url = url


class WebSocket:
    def __init__(
        self, http: HttpConnection, stream_id: int, transmit: Callable[[], None]
    ) -> None:
        self.http = http
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.stream_id = stream_id
        self.subprotocol: Optional[str] = None
        self.transmit = transmit
        self.websocket = wsproto.Connection(wsproto.ConnectionType.CLIENT)

    async def close(self, code=1000, reason="") -> None:
        """
        Perform the closing handshake.
        """
        data = self.websocket.send(
            wsproto.events.CloseConnection(code=code, reason=reason)
        )
        self.http.send_data(stream_id=self.stream_id, data=data, end_stream=True)
        self.transmit()

    async def recv(self) -> str:
        """
        Receive the next message.
        """
        return await self.queue.get()

    async def send(self, message: str) -> None:
        """
        Send a message.
        """
        assert isinstance(message, str)

        data = self.websocket.send(wsproto.events.TextMessage(data=message))
        self.http.send_data(stream_id=self.stream_id, data=data, end_stream=False)
        self.transmit()

    def http_event_received(self, event: H3Event) -> None:
        if isinstance(event, HeadersReceived):
            for header, value in event.headers:
                if header == b"sec-websocket-protocol":
                    self.subprotocol = value.decode()
        elif isinstance(event, DataReceived):
            self.websocket.receive_data(event.data)

        for ws_event in self.websocket.events():
            self.websocket_event_received(ws_event)

    def websocket_event_received(self, event: wsproto.events.Event) -> None:
        if isinstance(event, wsproto.events.TextMessage):
            self.queue.put_nowait(event.data)


class HttpClient(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.pushes: Dict[int, Deque[H3Event]] = {}
        self._http: Optional[HttpConnection] = None
        self._request_events: Dict[int, Deque[H3Event]] = {}
        self._request_waiter: Dict[int, asyncio.Future[Deque[H3Event]]] = {}
        self._websockets: Dict[int, WebSocket] = {}

        if self._quic.configuration.alpn_protocols[0].startswith("hq-"):
            self._http = H0Connection(self._quic)
        else:
            self._http = H3Connection(self._quic)

    async def get(self, url: str, headers: Dict = {}) -> Deque[H3Event]:
        """
        Perform a GET request.
        """
        return await self._request(
            HttpRequest(method="GET", url=URL(url), headers=headers)
        )

    async def post(self, url: str, data: bytes, headers: Dict = {}) -> Deque[H3Event]:
        """
        Perform a POST request.
        """
        return await self._request(
            HttpRequest(method="POST", url=URL(url), content=data, headers=headers)
        )

    async def websocket(self, url: str, subprotocols: List[str] = []) -> WebSocket:
        """
        Open a WebSocket.
        """
        request = HttpRequest(method="CONNECT", url=URL(url))
        stream_id = self._quic.get_next_available_stream_id()
        websocket = WebSocket(
            http=self._http, stream_id=stream_id, transmit=self.transmit
        )

        self._websockets[stream_id] = websocket

        headers = [
            (b":method", b"CONNECT"),
            (b":scheme", b"https"),
            (b":authority", request.url.authority.encode()),
            (b":path", request.url.full_path.encode()),
            (b":protocol", b"websocket"),
            (b"user-agent", USER_AGENT.encode()),
            (b"sec-websocket-version", b"13"),
        ]
        if subprotocols:
            headers.append(
                (b"sec-websocket-protocol", ", ".join(subprotocols).encode())
            )
        self._http.send_headers(stream_id=stream_id, headers=headers)

        self.transmit()

        return websocket

    def http_event_received(self, event: H3Event) -> None:
        if isinstance(event, (HeadersReceived, DataReceived)):
            stream_id = event.stream_id
            if stream_id in self._request_events:
                # http
                self._request_events[event.stream_id].append(event)
                if event.stream_ended:
                    request_waiter = self._request_waiter.pop(stream_id)
                    request_waiter.set_result(self._request_events.pop(stream_id))

            elif stream_id in self._websockets:
                # websocket
                websocket = self._websockets[stream_id]
                websocket.http_event_received(event)

            elif event.push_id in self.pushes:
                # push
                self.pushes[event.push_id].append(event)

        elif isinstance(event, PushPromiseReceived):
            self.pushes[event.push_id] = deque()
            self.pushes[event.push_id].append(event)

    def quic_event_received(self, event: QuicEvent) -> None:
        #  pass event to the HTTP layer
        if self._http is not None:
            for http_event in self._http.handle_event(event):
                self.http_event_received(http_event)

    async def _request(self, request: HttpRequest) -> Deque[H3Event]:
        stream_id = self._quic.get_next_available_stream_id()
        self._http.send_headers(
            stream_id=stream_id,
            headers=[
                (b":method", request.method.encode()),
                (b":scheme", request.url.scheme.encode()),
                (b":authority", request.url.authority.encode()),
                (b":path", request.url.full_path.encode()),
                (b"user-agent", USER_AGENT.encode()),
            ]
            + [(k.encode(), v.encode()) for (k, v) in request.headers.items()],
        )
        self._http.send_data(stream_id=stream_id, data=request.content, end_stream=True)

        waiter = self._loop.create_future()
        self._request_events[stream_id] = deque()
        self._request_waiter[stream_id] = waiter
        self.transmit()

        return await asyncio.shield(waiter)


def parse_response (http_events: Deque[H3Event]) -> None:
    headers = attrdict.CaseInsensitiveDict ()
    contents = []
    stream_id = None
    for http_event in http_events:
        if isinstance(http_event, HeadersReceived):
            stream_id = http_event.stream_id
            for k, v in http_event.headers:
                headers [k.decode ()] = v.decode ()
        elif isinstance(http_event, DataReceived):
            contents.append (http_event.data)
    return stream_id, headers, b''.join (contents)

async def perform_http_request(client, url, data, request):
    # perform request
    start = time.time()
    if data is not None:
        http_events = await client.post(
            url,
            data = data,
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        method = "POST"
    else:
        http_events = await client.get(url)
        method = "GET"
    elapsed = time.time() - start

    # print speed
    octets = 0
    for http_event in http_events:
        if isinstance(http_event, DataReceived):
            octets += len(http_event.data)
    logger.info(
        "Response received for %s %s : %d bytes in %.1f s (%.3f Mbps)"
        % (method, urlparse(url).path, octets, elapsed, octets * 8 / elapsed / 1000000)
    )

    output_file = BytesIO ()
    stream_id, headers, content = parse_response (http_events)
    request.response = HttpResponse (stream_id, headers, content, http_events)

def process_http_pushes(client, requests):
    d = { r.response.stream_id: r for r in requests }
    for _, http_events in client.pushes.items():
        method = ""
        octets = 0
        path = ""
        origin_stream_id = 0
        push_id = 0
        for http_event in http_events:
            if isinstance(http_event, DataReceived):
                octets += len(http_event.data)
            elif isinstance(http_event, PushPromiseReceived):
                origin_stream_id = http_event.stream_id
                push_id = http_event.push_id
                for header, value in http_event.headers:
                    if header == b":method":
                        method = value.decode()
                    elif header == b":path":
                        path = value.decode()

        logger.info("Push received for %s %s : %s bytes", method, path, octets)
        stream_id, headers, content = parse_response (http_events)
        r = HttpResponse (stream_id, headers, content, http_events, path, method, push_id)
        if origin_stream_id in d:
            d [origin_stream_id].response.add_promise (r)


def save_session_ticket(ticket: SessionTicket) -> None:
    """
    Callback which is invoked by the TLS engine when a new session ticket
    is received.
    """
    logger.info("New session ticket received")

async def run(
    configuration,
    requests,
    local_port=0,
    zero_rtt=False
) -> None:
    request = requests [0]
    parsed = urlparse (request.url)
    assert parsed.scheme in ("https", "wss",), "Only https:// or wss:// URLs are supported."
    host = parsed.hostname
    if parsed.port is not None:
        port = parsed.port
    else:
        port = 443

    async with connect(
        host,
        port,
        configuration=configuration,
        create_protocol=HttpClient,
        session_ticket_handler=save_session_ticket,
        local_port=local_port,
        wait_connected=not zero_rtt,
    ) as client:

        client = cast(HttpClient, client)
        # perform request
        coros = []
        for r in requests:
            coros.append (perform_http_request (
                client=client,
                url=r.url,
                data=r.content,
                request = r
            ))

        await asyncio.gather(*coros)
        process_http_pushes (client, requests)


class HttpResponse (h2client.HttpResponse):
    def __init__ (self, stream_id, headers, content, events, path = None, method = None, push_id = None):
        self.stream_id = stream_id
        self.headers = headers
        self.content = content
        self.events = events
        self.path = path
        self.method = method
        self.push_id = push_id
        self.status_code = int (self.headers.get (':status', 200))
        self.reason = ''
        self.promises = []

    def add_promise (self, promise):
        self.promises.append (promise)


class Request:
    def __init__(self, method, url, content = None, headers = {}, allow_push = True):
        self.args = (method, url, content, headers, allow_push)
        self.content = content
        if isinstance (self.content, dict):
            self.content = urlencode (content)
        if isinstance (self.content, str):
            self.content = self.content.encode ("utf8")
        self.headers = headers
        self.method = method
        self.url = url
        self.allow_push = allow_push
        self.response = None

    def clone (self):
        return Request (*self.args)


class Session (h2client.Session):
    def __init__ (self, endpoint):
        parts = urlparse (endpoint)
        self.endpoint = 'https://' + parts.netloc
        self.configuration = QuicConfiguration(is_client=True, alpn_protocols=H3_ALPN)
        self.configuration.verify_mode = ssl.CERT_NONE

    def _request_all (self, requests):
        loop = asyncio.get_event_loop()
        loop.run_until_complete (
            run (
                self.configuration,
                requests,
                local_port=0,
                zero_rtt=False
            )
        )

    def _request (self, method, urls, data = None, headers = {}):
        issingle = False
        if isinstance (urls, str):
            issingle = True
            urls = [urls]
        rs = [ Request (method.upper (), self.endpoint + url, data, headers, allow_push = True) for url in urls ]
        self._request_all (rs)
        return rs [0].response if issingle else [ r.response for r in rs ]


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )
    s = Session ('https://127.0.0.1:4433')

    r = s.post ('/hello', {'num': '10'})
    print (r.status_code)
    print (r.headers)
    print (r.content)

    r = s.get ('/hello')
    print (r.status_code)
    print (r.headers)
    print (r.content)

    r = s.get (['/hello'])
    print (r)

