"""Section 8.2 — WS /ws/feed.

Zero-install adaptation: a minimal RFC 6455 WebSocket server implemented
on the standard library (hashlib/base64/struct over the raw socket that
http.server already owns). Message envelope is exactly:

    {"type": "story_created" | "story_updated" | "instability_updated",
     "payload": { ... },
     "timestamp": "..."}

The hub broadcasts on new story inserts/updates and instability updates.
Clients that disappear are pruned silently; the frontend's reconnect /
15-second REST-polling fallback (Section 8.2) covers the rest.
"""

import base64
import hashlib
import json
import logging
import struct
import threading

from ..db.models import now_iso

log = logging.getLogger("ws")

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def accept_key(client_key: str) -> str:
    digest = hashlib.sha1((client_key + WS_GUID).encode()).digest()
    return base64.b64encode(digest).decode()


def encode_text_frame(text: str) -> bytes:
    payload = text.encode()
    length = len(payload)
    if length < 126:
        header = struct.pack("!BB", 0x81, length)
    elif length < 65536:
        header = struct.pack("!BBH", 0x81, 126, length)
    else:
        header = struct.pack("!BBQ", 0x81, 127, length)
    return header + payload


def _encode_control(opcode: int, payload: bytes = b"") -> bytes:
    return struct.pack("!BB", 0x80 | opcode, len(payload)) + payload


class FeedHub:
    def __init__(self) -> None:
        self._clients: set = set()
        self._lock = threading.Lock()

    def register(self, sock) -> None:
        with self._lock:
            self._clients.add(sock)
        log.info("ws_connected", extra={"data": {"clients": len(self._clients)}})

    def unregister(self, sock) -> None:
        with self._lock:
            self._clients.discard(sock)
        try:
            sock.close()
        except OSError:
            pass

    def broadcast(self, msg_type: str, payload: dict) -> None:
        envelope = json.dumps({"type": msg_type, "payload": payload,
                               "timestamp": now_iso()}, default=str)
        frame = encode_text_frame(envelope)
        with self._lock:
            clients = list(self._clients)
        dead = []
        for sock in clients:
            try:
                sock.sendall(frame)
            except OSError:
                dead.append(sock)
        for sock in dead:
            self.unregister(sock)
        if clients:
            log.debug("ws_broadcast", extra={"data": {"type": msg_type,
                                                      "clients": len(clients)}})


hub = FeedHub()


def _read_exact(sock, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("socket closed")
        buf += chunk
    return buf


def serve_connection(sock) -> None:
    """Reader loop: answers pings, honors close; incoming text is ignored
    (the feed is server-push only)."""
    hub.register(sock)
    try:
        while True:
            b1, b2 = _read_exact(sock, 2)
            opcode = b1 & 0x0F
            masked = b2 & 0x80
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack("!H", _read_exact(sock, 2))[0]
            elif length == 127:
                length = struct.unpack("!Q", _read_exact(sock, 8))[0]
            mask = _read_exact(sock, 4) if masked else b"\x00" * 4
            payload = bytearray(_read_exact(sock, length)) if length else bytearray()
            for i in range(length):
                payload[i] ^= mask[i % 4]
            if opcode == 0x8:  # close
                try:
                    sock.sendall(_encode_control(0x8))
                except OSError:
                    pass
                break
            if opcode == 0x9:  # ping -> pong
                sock.sendall(_encode_control(0xA, bytes(payload)))
    except (ConnectionError, OSError, struct.error):
        pass
    finally:
        hub.unregister(sock)
