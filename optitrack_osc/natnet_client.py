"""NatNet 4.0 UDP client for Motive 2.3.0."""

import logging
import math
import socket
import struct
import threading
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

log = logging.getLogger(__name__)

_NAT_CONNECT = 0
_NAT_REQUEST_MODELDEF = 4
_NAT_MODELDEF = 5
_NAT_FRAMEOFDATA = 7

MULTICAST_ADDRESS = "239.255.42.99"
COMMAND_PORT = 1510
DATA_PORT = 1511


@dataclass
class RigidBody:
    id: int
    name: str
    x: float
    y: float
    z: float
    yaw: float          # degrees, rotation around Z
    pitch: float        # degrees, rotation around Y
    roll: float         # degrees, rotation around X
    tracking_valid: bool


def _quat_to_euler_deg(qx: float, qy: float, qz: float, qw: float):
    """Convert quaternion to ZYX Tait-Bryan Euler angles in degrees."""
    roll = math.degrees(math.atan2(
        2.0 * (qw * qx + qy * qz),
        1.0 - 2.0 * (qx * qx + qy * qy),
    ))
    sinp = max(-1.0, min(1.0, 2.0 * (qw * qy - qz * qx)))
    pitch = math.degrees(math.asin(sinp))
    yaw = math.degrees(math.atan2(
        2.0 * (qw * qz + qx * qy),
        1.0 - 2.0 * (qy * qy + qz * qz),
    ))
    return yaw, pitch, roll


def _read_str(data: bytes, offset: int) -> tuple[str, int]:
    end = data.index(b"\x00", offset)
    return data[offset:end].decode("utf-8", errors="replace"), end + 1


class NatNetClient:
    def __init__(
        self,
        server_ip: str,
        local_ip: str = "0.0.0.0",
        on_rigid_bodies: Optional[Callable[[List[RigidBody]], None]] = None,
    ):
        self.server_ip = server_ip
        self.local_ip = local_ip
        self.on_rigid_bodies = on_rigid_bodies
        self._names: Dict[int, str] = {}
        self._running = False
        self._cmd_sock: Optional[socket.socket] = None
        self._data_sock: Optional[socket.socket] = None

    # ── public ───────────────────────────────────────────────────────────────

    def start(self):
        self._running = True
        self._cmd_sock = self._open_command_socket()
        self._data_sock = self._open_data_socket()
        # Announce ourselves and request rigid body name map
        self._send(_NAT_CONNECT, b"\x04\x00\x00\x00\x04\x00\x00\x00")
        self._send(_NAT_REQUEST_MODELDEF)
        threading.Thread(target=self._recv_loop, args=(self._cmd_sock,), daemon=True).start()
        threading.Thread(target=self._recv_loop, args=(self._data_sock,), daemon=True).start()

    def stop(self):
        self._running = False
        for s in (self._cmd_sock, self._data_sock):
            if s:
                try:
                    s.close()
                except OSError:
                    pass

    # ── sockets ───────────────────────────────────────────────────────────────

    def _open_command_socket(self) -> socket.socket:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", 0))
        s.settimeout(0.5)
        return s

    def _open_data_socket(self) -> socket.socket:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", DATA_PORT))
        mreq = struct.pack("4s4s",
                           socket.inet_aton(MULTICAST_ADDRESS),
                           socket.inet_aton("0.0.0.0"))
        s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        s.settimeout(1.0)
        return s

    def _send(self, msg_id: int, payload: bytes = b""):
        packet = struct.pack("<HH", msg_id, len(payload)) + payload
        self._cmd_sock.sendto(packet, (self.server_ip, COMMAND_PORT))

    # ── receive ───────────────────────────────────────────────────────────────

    def _recv_loop(self, sock: socket.socket):
        while self._running:
            try:
                data, _ = sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                self._dispatch(data)
            except Exception as exc:
                log.debug("parse error: %s", exc)

    def _dispatch(self, data: bytes):
        if len(data) < 4:
            return
        msg_id, = struct.unpack_from("<H", data, 0)
        payload = data[4:]
        if msg_id == _NAT_FRAMEOFDATA:
            self._parse_frame(payload)
        elif msg_id == _NAT_MODELDEF:
            self._parse_model_def(payload)

    # ── model definitions (name map) ──────────────────────────────────────────

    def _parse_model_def(self, data: bytes):
        offset = 0
        count, = struct.unpack_from("<i", data, offset)
        offset += 4
        for _ in range(count):
            asset_type, = struct.unpack_from("<i", data, offset)
            offset += 4
            if asset_type == 0:         # MarkerSet
                _, offset = _read_str(data, offset)
                m, = struct.unpack_from("<i", data, offset)
                offset += 4
                for __ in range(m):     # marker names
                    _, offset = _read_str(data, offset)
            elif asset_type == 1:       # RigidBody
                name, offset = _read_str(data, offset)
                rb_id, = struct.unpack_from("<i", data, offset)
                offset += 4
                offset += 16            # parent_id(4) + offset_xyz(12)
                m, = struct.unpack_from("<i", data, offset)
                offset += 4
                offset += m * 16        # position(12) + active_label(4) per marker
                self._names[rb_id] = name
                log.info("Registered rigid body %d = %r", rb_id, name)
            elif asset_type == 2:       # Skeleton — parse bones as rigid body defs
                _, offset = _read_str(data, offset)
                offset += 4             # skeleton id
                bones, = struct.unpack_from("<i", data, offset)
                offset += 4
                for __ in range(bones):
                    _, offset = _read_str(data, offset)
                    offset += 4 + 16    # id + parent_id + offset_xyz
                    m, = struct.unpack_from("<i", data, offset)
                    offset += 4
                    offset += m * 16
            else:
                break                   # unknown type; stop safely

    # ── frame data ────────────────────────────────────────────────────────────

    def _parse_frame(self, data: bytes):
        offset = 4  # skip frame number (int32)

        # Marker sets
        count, = struct.unpack_from("<i", data, offset)
        offset += 4
        for _ in range(count):
            _, offset = _read_str(data, offset)
            m, = struct.unpack_from("<i", data, offset)
            offset += 4 + m * 12

        # Unlabeled markers
        count, = struct.unpack_from("<i", data, offset)
        offset += 4 + count * 12

        # Rigid bodies
        count, = struct.unpack_from("<i", data, offset)
        offset += 4
        bodies: List[RigidBody] = []
        for _ in range(count):
            rb_id, = struct.unpack_from("<i", data, offset)
            offset += 4
            x, y, z = struct.unpack_from("<fff", data, offset)
            offset += 12
            qx, qy, qz, qw = struct.unpack_from("<ffff", data, offset)
            offset += 16
            offset += 4                 # mean marker error (float)
            params, = struct.unpack_from("<h", data, offset)
            offset += 2
            yaw, pitch, roll = _quat_to_euler_deg(qx, qy, qz, qw)
            bodies.append(RigidBody(
                id=rb_id,
                name=self._names.get(rb_id, str(rb_id)),
                x=x, y=y, z=z,
                yaw=yaw, pitch=pitch, roll=roll,
                tracking_valid=bool(params & 0x01),
            ))

        if bodies and self.on_rigid_bodies:
            self.on_rigid_bodies(bodies)
