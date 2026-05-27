# OptitrackOSC

A program that reads OptiTrack rigid body data from Motive 2.3.0 via NatNet and forwards it as OSC messages containing position (x, y, z) and orientation (yaw, pitch, roll) to a configurable host and port.

## Project Plan

### Phase 1 — NatNet receiver
- Connect to Motive 2.3.0 using the NatNet SDK (or a compatible Python client such as `natnetclient` / direct UDP parsing)
- Subscribe to rigid body frame data
- Extract per-rigid-body position (x, y, z) and quaternion orientation, convert to angles in degree (yaw, pitch, roll)

### Phase 2 — OSC sender
- Use `python-osc` to build and send OSC messages
- Address pattern: `/optitrack/<rigid_body_name>/position` → float x, y, z
- Address pattern: `/optitrack/<rigid_body_name>/rotation` → float yaw, pitch, roll
- Configurable target host IP and port (CLI args or config file)

### Phase 3 — Configuration & UX
- CLI entry point with `--server-ip`, `--server-port`, `--osc-host`, `--osc-port` arguments
- Optional: config file (TOML or similar) for persistent settings
- Graceful shutdown on Ctrl-C

### Phase 4 — Packaging & docs
- `pyproject.toml` with dependencies
- Basic README with usage instructions

## Tech Stack
- **Language**: Python 3.11+
- **NatNet client**: NatNet SDK Python sample or `natnetclient` library (multicast UDP)
- **OSC**: `python-osc`
- **Config/CLI**: `argparse` or `click`

## NatNet Notes (Motive 2.3.0)
- Default command port: 1510 (unicast) or multicast group 239.255.42.99
- Default data port: 1511
- Protocol version: NatNet 4.0 (Motive 2.3)
- Rigid body data includes position as (x, y, z) in meters and orientation as quaternion (qx, qy, qz, qw)
- Euler conversion order: ZYX (yaw = Z, pitch = Y, roll = X) using scipy or manual quaternion math

## File Structure (planned)
```
OptitrackOSC/
├── CLAUDE.md
├── pyproject.toml
├── README.md
└── optitrack_osc/
    ├── __init__.py
    ├── __main__.py       # entry point
    ├── natnet_client.py  # NatNet UDP receiver
    ├── osc_sender.py     # OSC message builder/sender
    └── config.py         # CLI args & config
```
