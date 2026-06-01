"""OSC sender for rigid body position and rotation."""

import logging
import re
from typing import List

from pythonosc import udp_client

from .natnet_client import RigidBody

log = logging.getLogger(__name__)


def _sanitize(name: str) -> str:
    """Replace characters invalid in an OSC address path segment with underscores."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", name) or "unknown"


class OscSender:
    def __init__(self, host: str, port: int, rotation_format: str = "euler"):
        self._client = udp_client.SimpleUDPClient(host, port)
        self._host = host
        self._port = port
        self._quaternion = rotation_format == "quaternion"

    def send(self, bodies: List[RigidBody]):
        for rb in bodies:
            seg = _sanitize(rb.name)
            self._client.send_message(
                f"/optitrack/{seg}/position",
                [rb.x, rb.y, rb.z],
            )
            if self._quaternion:
                self._client.send_message(
                    f"/optitrack/{seg}/rotation",
                    [rb.qw, rb.qx, rb.qy, rb.qz],
                )
                log.debug(
                    "%s  pos=(%.3f, %.3f, %.3f)  quat=(%.4f, %.4f, %.4f, %.4f)  valid=%s",
                    seg, rb.x, rb.y, rb.z, rb.qw, rb.qx, rb.qy, rb.qz, rb.tracking_valid,
                )
            else:
                self._client.send_message(
                    f"/optitrack/{seg}/rotation",
                    [rb.yaw, rb.pitch, rb.roll],
                )
                log.debug(
                    "%s  pos=(%.3f, %.3f, %.3f)  rot=(%.1f°, %.1f°, %.1f°)  valid=%s",
                    seg, rb.x, rb.y, rb.z, rb.yaw, rb.pitch, rb.roll, rb.tracking_valid,
                )
