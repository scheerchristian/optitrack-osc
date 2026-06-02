# optitrack-osc

Reads rigid body data from a **Motive 2.3.0** OptiTrack stream (NatNet 4.0) and forwards position and orientation as OSC messages to any host and port you choose.

Each tracked rigid body produces two OSC messages per frame:

```
/optitrack/<name>/position   float x  float y  float z               (metres)
/optitrack/<name>/rotation   float yaw  float pitch  float roll       (degrees, default)
                         — or —
/optitrack/<name>/rotation   float w  float x  float y  float z      (quaternion)
```

The rotation format is selectable at startup (see `--rotation-format` below). The default is Euler angles using the **YXZ Tait-Bryan** convention (yaw = rotation around Y, pitch = X, roll = Z), which matches Motive's Y-up coordinate system.

---

## Requirements

- [Anaconda](https://www.anaconda.com/download) or Miniconda
- **Motive 2.3.0** running on the same machine or network, with *Broadcast Frame Data* enabled and the streaming interface set to the correct network adapter

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/scheerchristian/optitrack-osc.git
cd optitrack-osc
```

### 2. Create a Conda environment

```bash
conda create -n optitrack-osc python=3.11
conda activate optitrack-osc
```

### 3. Install the package

```bash
pip install -e .
```

This installs `python-osc` and registers the `optitrack-osc` command inside the active environment.

---

## Motive setup

1. Open Motive 2.3.0 and go to **Edit → Settings → Streaming**.
2. Make sure **Broadcast Frame Data** is checked.
3. Set **Local Interface** to the network adapter that connects to the machine running OptitrackOSC.
4. Leave the default multicast address (`239.255.42.99`) and ports (command `1510`, data `1511`) unchanged unless you have a reason to change them.
5. Create one or more **Rigid Body** assets in Motive. Their names will appear in the OSC address path.

---

## Usage

Make sure the Conda environment is active first:

```bash
conda activate optitrack-osc
```

### Same machine as Motive

```bash
optitrack-osc
```

### Motive on a different machine

```bash
optitrack-osc --server-ip 192.168.1.10
```

### Send OSC to a remote host

```bash
optitrack-osc --server-ip 192.168.1.10 --osc-host 192.168.1.20 --osc-port 8000
```

### Send quaternions instead of Euler angles

```bash
optitrack-osc --rotation-format quaternion
```

### All options

```
optitrack-osc --help

  --server-ip       IP      Motive machine IP address             (default: 127.0.0.1)
  --local-ip        IP      Local network interface for multicast  (default: 0.0.0.0)
  --osc-host        IP      OSC target host                       (default: 127.0.0.1)
  --osc-port        PORT    OSC target port                       (default: 9000)
  --rotation-format FORMAT  euler or quaternion                   (default: euler)
  -v, --verbose             Enable debug logging
```

### Verbose mode (shows every frame in the terminal)

```bash
optitrack-osc --server-ip 192.168.1.10 -v
```

---

## OSC message reference

| Address | Arguments | Notes |
|---|---|---|
| `/optitrack/<name>/position` | `x y z` (float, metres) | World-space position |
| `/optitrack/<name>/rotation` | `yaw pitch roll` (float, degrees) | YXZ Tait-Bryan Euler angles (`--rotation-format euler`, default) |
| `/optitrack/<name>/rotation` | `w x y z` (float) | Unit quaternion (`--rotation-format quaternion`) |

`<name>` is the rigid body name set in Motive. Spaces and special characters are replaced with underscores.

---

## Measurement workflow

### Motive setup (do once per session)

1. Make sure **Edit → Settings → Streaming → Up Axis** is set to **Y Up**.
2. Place the passive tracker flat on a table in its intended neutral orientation, fully visible to the cameras.
3. In the **Assets** pane, right-click the rigid body → **Reset Pivot**. This makes the current pose the zero reference (identity quaternion). Name the rigid body **head** if you are using benchmark-headtracker.
4. Confirm tracking is stable (solid marker colours, low mean error).

### Start optitrack-osc

```bash
conda activate optitrack-osc
optitrack-osc
```

No further calibration is needed in this app — Motive's Reset Pivot defines the zero.

---

### Optional: benchmark with benchmark-headtracker

[benchmark-headtracker](https://github.com/scheerchristian/benchmark-headtracker) compares the OptiTrack stream against a webcam-based head tracker across four scenarios: stable grid positions, trajectory following, drift, and latency.

#### One-time configuration

Open `head_tracker_benchmark.py` and confirm the constants at the top match your setup:

```python
OPTITRACK_PORT = 8001
OPTITRACK_ADDR = "/optitrack/head/rotation"   # must end in /rotation, not /quaternion

WEBCAM_PORT = 8000
WEBCAM_ADDR = "/Virtuoso/quat"                # address sent by your webcam tracker
```

#### Per-session steps

1. Start optitrack-osc in **quaternion** mode, targeting the benchmark port:

   ```bash
   optitrack-osc --osc-port 8001 --rotation-format quaternion
   ```

2. Start your webcam head tracker and make sure it is sending OSC to port `8000`.

3. Start the benchmark:

   ```bash
   conda activate benchmark-headtracker   # or whichever env has the dependencies
   python head_tracker_benchmark.py
   ```

4. The benchmark waits 2 seconds for both OSC streams to appear, then reports whether each source is live. Calibrate inside the benchmark when prompted — OptiTrack's pivot reset already defines the mechanical zero, so the benchmark calibration only aligns the two trackers' coordinate frames against each other.

5. Follow the on-screen guidance for each measurement mode. Results are saved to `benchmark_data/<timestamp>/`.

---

## Troubleshooting

**No data arrives**
- Confirm *Broadcast Frame Data* is enabled in Motive.
- Make sure the *Local Interface* in Motive is set to the adapter on the same subnet as your machine, not `127.0.0.1` or `0.0.0.0`.
- Windows Firewall may block multicast UDP. Add an inbound rule for UDP port `1511` if needed.

**Rigid body names show as numbers**
- The model definition request did not complete before the first frame arrived. Names resolve within a second; if they never appear, check the `--server-ip` value and firewall rules on port `1510`.

**`optitrack-osc` command not found**
- Make sure the Conda environment is activated: `conda activate optitrack-osc`
