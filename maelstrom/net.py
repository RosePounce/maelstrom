"""Network transport for the two-player co-op, on a local network.

Taken from purr-tage (`purrtage/net.py`): length-prefixed JSON messages over
TCP, read in a thread so the game loop never blocks on the network, and a UDP
broadcast beacon so the other machine finds the host without typing an
address.

Unlike purr-tage, Maelstrom does not run in lockstep: the HOST simulates the
sector and sends a snapshot of it on every frame, the CLIENT only sends its
inputs (see `session/coop.py`). TCP on a local network is fast enough for that.

Desktop only: a browser page (pygbag) has no sockets.
"""

import json
import queue
import socket
import struct
import threading
import time

from maelstrom import i18n

PORT = 50517                 # game port (TCP)
BEACON_PORT = 50518          # advertisement port (UDP, broadcast)
BEACON_PERIOD = 1.0
# A flat refusal when the two versions differ: the snapshot format is shared.
PROTOCOL = 1
BEACON_GAME = "maelstrom"    # the game signature in the UDP advertisements
MAX_MESSAGE = 1 << 20        # guard rail: 1 MiB per message

HEADER = struct.Struct("!I")


def local_ip():
    """This machine's address on the local network, to show it to the other one."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))   # no data is ever sent
        return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"
    finally:
        s.close()


# --------------------------------------------------------------------- link --
class Link:
    """An established connection. Reads happen in a separate thread so that
    the game loop never blocks on the network."""

    def __init__(self, sock, peer=None):
        self.sock = sock
        self.peer = peer or sock.getpeername()[0]
        self.inbox = queue.Queue()
        self.alive = True
        self.error = None
        self._send_lock = threading.Lock()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf

    def _read_loop(self):
        try:
            while self.alive:
                head = self._recv_exact(HEADER.size)
                if head is None:
                    break
                (size,) = HEADER.unpack(head)
                if size <= 0 or size > MAX_MESSAGE:
                    raise ValueError("invalid message size: %d" % size)
                body = self._recv_exact(size)
                if body is None:
                    break
                self.inbox.put(json.loads(body.decode("utf-8")))
        except Exception as exc:
            self.error = str(exc)
        finally:
            self.alive = False

    def send(self, message):
        if not self.alive:
            return False
        body = json.dumps(message, separators=(",", ":")).encode("utf-8")
        try:
            with self._send_lock:
                self.sock.sendall(HEADER.pack(len(body)) + body)
            return True
        except Exception as exc:
            self.error = str(exc)
            self.alive = False
            return False

    def poll(self):
        """Every message received since the last call."""
        out = []
        while True:
            try:
                out.append(self.inbox.get_nowait())
            except queue.Empty:
                return out

    def close(self, farewell=True):
        """Closes the link; by default first tells the other side, so that it
        shows "partner left" rather than waiting on a dead link."""
        if farewell and self.alive:
            self.send({"type": "bye"})
        self.alive = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass


# --------------------------------------------------------------------- host --
class Host:
    """Wait for a partner and advertise on the local network. Raises OSError
    when the port is taken (another host already runs on this machine)."""

    def __init__(self, name=None, port=PORT, announce=True):
        self.name = name or i18n.t("lan.default_host_name", host=socket.gethostname())
        self.port = port
        self.link = None
        self.error = None
        self.ip = local_ip()
        self._stop = threading.Event()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", port))
        self.sock.listen(1)
        self.sock.settimeout(0.2)
        self._accept = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept.start()
        if announce:
            threading.Thread(target=self._beacon_loop, daemon=True).start()

    def _accept_loop(self):
        while not self._stop.is_set() and self.link is None:
            try:
                conn, addr = self.sock.accept()
            except socket.timeout:
                continue
            except Exception as exc:
                self.error = str(exc)
                return
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.link = Link(conn, addr[0])

    def _beacon_loop(self):
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        payload = json.dumps({"game": BEACON_GAME, "protocol": PROTOCOL,
                              "name": self.name, "port": self.port}).encode("utf-8")
        while not self._stop.is_set() and self.link is None:
            try:
                udp.sendto(payload, ("255.255.255.255", BEACON_PORT))
            except Exception:
                pass
            self._stop.wait(BEACON_PERIOD)
        udp.close()

    def release(self):
        """Stops listening and advertising, KEEPING the link: it now belongs
        to the game."""
        self._stop.set()
        try:
            self.sock.close()
        except Exception:
            pass
        link, self.link = self.link, None
        return link

    def close(self):
        link = self.release()
        if link:
            link.close()


# ------------------------------------------------------------------- client --
def connect(address, port=PORT, timeout=4.0):
    """Join a host. Returns a link, or raises OSError."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((address, port))
    except OSError:
        sock.close()
        raise
    sock.settimeout(None)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return Link(sock, address)


class Browser:
    """Listen to the advertisements of the hosts on the local network."""

    def __init__(self, port=BEACON_PORT):
        self.found = {}                   # ip -> {name, port, protocol, seen}
        self.error = None
        self._stop = threading.Event()
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("", port))
            self.sock.settimeout(0.3)
        except Exception as exc:
            self.sock = None
            self.error = str(exc)
            return
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while not self._stop.is_set():
            try:
                data, addr = self.sock.recvfrom(2048)
            except socket.timeout:
                continue
            except Exception:
                return
            try:
                info = json.loads(data.decode("utf-8"))
            except Exception:
                continue
            if not isinstance(info, dict) or info.get("game") != BEACON_GAME:
                continue
            self.found[addr[0]] = {"name": str(info.get("name", "?"))[:32],
                                   "port": int(info.get("port", PORT)),
                                   "protocol": info.get("protocol"),
                                   "seen": time.time()}

    def hosts(self, max_age=4.0):
        """The hosts seen recently, sorted by address."""
        now = time.time()
        out = [(ip, d) for ip, d in self.found.items() if now - d["seen"] <= max_age]
        out.sort(key=lambda item: item[0])
        return out

    def close(self):
        self._stop.set()
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
