"""Local no-auth HTTP proxy bridge for authenticated upstream proxies."""

from __future__ import annotations

import base64
import select
import socket
import socketserver
import threading
from dataclasses import dataclass

from loguru import logger

from utils.proxy import ParsedProxy

BUFFER_SIZE = 64 * 1024


@dataclass(frozen=True)
class ProxyBridge:
    """Running local proxy bridge metadata."""

    server_url: str
    server: socketserver.ThreadingTCPServer
    thread: threading.Thread


class _ProxyBridgeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_proxy_bridge(parsed_proxy: ParsedProxy) -> ProxyBridge:
    """Start a local no-auth proxy that forwards to one authenticated upstream."""
    handler = _build_handler(parsed_proxy)
    server = _ProxyBridgeServer(("127.0.0.1", 0), handler)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, name="parserriba-proxy-bridge", daemon=True)
    thread.start()
    logger.info("Started local proxy bridge at http://{}:{}", host, port)
    return ProxyBridge(server_url=f"http://{host}:{port}", server=server, thread=thread)


def _build_handler(parsed_proxy: ParsedProxy) -> type[socketserver.BaseRequestHandler]:
    class ProxyBridgeHandler(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            try:
                first = self.request.recv(BUFFER_SIZE)
                if not first:
                    return
                first_line = first.split(b"\r\n", 1)[0].decode("ascii", errors="ignore")
                if first_line.upper().startswith("CONNECT "):
                    _handle_connect(self.request, parsed_proxy, first_line)
                else:
                    _handle_http(self.request, parsed_proxy, first)
            except OSError:
                return

    return ProxyBridgeHandler


def _handle_connect(client: socket.socket, parsed_proxy: ParsedProxy, first_line: str) -> None:
    with _connect_upstream(parsed_proxy) as upstream:
        request = _connect_request(first_line, parsed_proxy)
        upstream.sendall(request)
        response = _read_until_headers(upstream)
        client.sendall(response)
        if b" 200 " not in response.split(b"\r\n", 1)[0]:
            return
        _relay(client, upstream)


def _handle_http(client: socket.socket, parsed_proxy: ParsedProxy, first: bytes) -> None:
    with _connect_upstream(parsed_proxy) as upstream:
        upstream.sendall(_inject_proxy_auth(first, parsed_proxy))
        _relay(client, upstream)


def _connect_upstream(parsed_proxy: ParsedProxy) -> socket.socket:
    server = parsed_proxy.server.replace("http://", "", 1)
    host, port_text = server.rsplit(":", 1)
    return socket.create_connection((host, int(port_text)), timeout=30)


def _connect_request(first_line: str, parsed_proxy: ParsedProxy) -> bytes:
    target = first_line.split(" ", 2)[1]
    return (
        f"CONNECT {target} HTTP/1.0\r\n"
        f"{_proxy_auth_header(parsed_proxy)}"
        "\r\n"
    ).encode("utf-8")


def _inject_proxy_auth(first: bytes, parsed_proxy: ParsedProxy) -> bytes:
    if b"\r\n\r\n" not in first:
        return first
    head, body = first.split(b"\r\n\r\n", 1)
    if b"\r\nProxy-Authorization:" in head:
        return first
    auth = _proxy_auth_header(parsed_proxy).strip().encode("ascii")
    return head + b"\r\n" + auth + b"\r\n\r\n" + body


def _proxy_auth_header(parsed_proxy: ParsedProxy) -> str:
    if not parsed_proxy.username or not parsed_proxy.password:
        return ""
    token = base64.b64encode(f"{parsed_proxy.username}:{parsed_proxy.password}".encode("utf-8")).decode("ascii")
    return f"Proxy-Authorization: Basic {token}\r\n"


def _read_until_headers(sock: socket.socket) -> bytes:
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = sock.recv(BUFFER_SIZE)
        if not chunk:
            break
        data += chunk
    return data


def _relay(left: socket.socket, right: socket.socket) -> None:
    sockets = [left, right]
    while True:
        readable, _, errored = select.select(sockets, [], sockets, 60)
        if errored or not readable:
            return
        for sock in readable:
            other = right if sock is left else left
            data = sock.recv(BUFFER_SIZE)
            if not data:
                return
            other.sendall(data)
