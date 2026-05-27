"""CLI argument parsing."""

import argparse


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Forward OptiTrack rigid body data from Motive 2.3 via OSC."
    )
    p.add_argument(
        "--server-ip", default="127.0.0.1", metavar="IP",
        help="IP address of the Motive machine (default: 127.0.0.1)",
    )
    p.add_argument(
        "--local-ip", default="0.0.0.0", metavar="IP",
        help="Local network interface to bind for multicast (default: 0.0.0.0)",
    )
    p.add_argument(
        "--osc-host", default="127.0.0.1", metavar="IP",
        help="OSC target host (default: 127.0.0.1)",
    )
    p.add_argument(
        "--osc-port", type=int, default=9000, metavar="PORT",
        help="OSC target port (default: 9000)",
    )
    p.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable debug logging",
    )
    return p.parse_args()
