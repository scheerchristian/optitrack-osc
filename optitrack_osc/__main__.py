"""Entry point."""

import logging
import time

from .config import parse_args
from .natnet_client import NatNetClient
from .osc_sender import OscSender


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    sender = OscSender(args.osc_host, args.osc_port, rotation_format=args.rotation_format)
    client = NatNetClient(
        server_ip=args.server_ip,
        local_ip=args.local_ip,
        on_rigid_bodies=sender.send,
    )

    print(f"Connecting to Motive at {args.server_ip} (NatNet multicast)")
    print(f"Forwarding OSC → {args.osc_host}:{args.osc_port}  rotation-format={args.rotation_format}")
    print("Press Ctrl-C to quit.\n")

    client.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down…")
    finally:
        client.stop()


if __name__ == "__main__":
    main()
