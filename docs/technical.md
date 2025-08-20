# BrightSide – Technical Deep-Dive

This document is aimed at **developers, packagers and advanced users** who
want to understand *exactly* how BrightSide works under the hood.  It
supplements the user-level docs in the project-root `README.md`.

---

## 1. Goals & Non-Goals

|                       | In scope                                   | *Not* in scope                 |
|-----------------------|---------------------------------------------|--------------------------------|
| **Goal G1**           | Let Ubuntu’s built-in brightness controls (GNOME slider & laptop Fn-keys) adjust *external* monitors. | Re-implementing a full GNOME Shell extension |
| **Goal G2**           | Provide a fallback GUI for systems where the built-in slider is unavailable. | Multi-platform support (macOS, Windows) |
| **Goal G3**           | Require zero configuration on common hardware. | Controlling displays without DDC/CI |

---

## 2. Components

### 2.1 `brightness_control/controller.py`

* **Language**: Python ≥ 3.8
* **Responsibility**: Thin façade over the *ddcutil* CLI to
  1. enumerate monitors (`ddcutil detect --brief`)
  2. read current brightness (`getvcp 10` → VCP 0x10)
  3. write brightness (`setvcp 10 $value`)
* **Error handling**: wraps `subprocess.*` exceptions in a custom
  `DDCUtilError` with human-friendly messages ready for Tk pop-ups.
* **Input sanitisation**: floats are rounded to `int` so that
  `58.04195…` → `58`; this avoids the *exit-status 1* bug we fixed.

````mermaid
flowchart TD
    python{{Python call}} --> |subprocess| ddcutil[(ddcutil)]
````

### 2.2 `brightness_sync.py`

* **Role**: Background daemon that *mirrors* laptop back-light brightness to
  every external monitor.
* **Algorithm**:
  1. Detect first back-light device under `/sys/class/backlight/*`.
  2. Read `max_brightness` once, then poll `brightness` every `POLL_INTERVAL`
     (default `0.2 s`).
  3. Convert the raw value to a percentage `round( val / max * 100 )`.
  4. If the percentage changed → call `controller.set_brightness(...)` for
     each detected display.
* **Performance**: each loop costs
  * ~0.1 ms for file I/O
  * 80-150 ms for spawning `ddcutil` and executing the I²C transaction.
* **Tuning**: decrease `POLL_INTERVAL` or replace the spawn with
  `libddcutil` for near-zero overhead.

### 2.3 `brightness_control/gui.py`

* **GUI Toolkit**: `Tkinter` with `ttkbootstrap` skins.
* **Widgets**: `OptionMenu` for display selection, `Scale` (0-100) as slider,
  text label showing numeric value.
* **Event pipeline**:
  1. On startup it calls `BrightnessController.list_monitors()`.
  2. On slider **move** `on_slider_move` updates the preview label.
  3. On slider **release** `on_slider_release` sets brightness (rounded int).
* **Threading**: GUI runs in main thread; all `ddcutil` invocations are
  synchronous.  Works fine because user interaction frequency is low.

### 2.4 `install_brightness_control.sh`

* **Purpose**: Simple deployment for non-technical users.
* **Key tasks**
  1. `apt install` – ensures `ddcutil`, Python 3, `python3-venv`, `python3-tk`.
  2. Copies the repo to `APP_DIR=/opt/brightness_control_gui` via `rsync`.
  3. Creates an *isolated* venv inside `$APP_DIR/venv` and installs Python deps
     from `requirements.txt` (presently `ttkbootstrap`, `Pillow`).
  4. Adds user to **i2c** group for `/dev/i2c-*` access.
  5. Generates a `.desktop` launcher that runs the GUI using the venv’s
     interpreter.
* **Update vs Install**: same function with a `force` flag; uses `rsync --delete`
  which makes updates idempotent.

### 2.5 systemd user service (optional)

We do *not* ship the unit file to keep root installer minimal; recommended
content:

```ini
[Unit]
Description=Mirror GNOME slider to external monitors (BrightSide)
After=graphical-session.target

[Service]
ExecStart=%h/.local/bin/brightness_sync
Restart=on-failure

[Install]
WantedBy=graphical-session.target
```

---

## 3. External Dependencies

| Dependency | Reason | Package on Ubuntu |
|------------|--------|-------------------|
| **ddcutil** | Talks DDC/CI over I²C | `ddcutil` |
| **Python 3.8+** | Runtime | `python3` |
| **python3-tk** | Tk bindings used by GUI | `python3-tk` |
| **python3-venv** | Create isolated env in installer | `python3-venv` |
| **ttkbootstrap** | Modern themed Tk widgets | pip package (requirements.txt) |
| **Pillow** | PNG icon support in Tk | pip package |

Kernel driver requirement: user must have read/write on `/dev/i2c-*` →
member of group *i2c*.  Installer ensures that.

---

## 4. Build & Test

```bash
# clone & create dev environment
git clone … && cd BrightSide
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
devpi install pytest black ruff   # optional

# run tests (if any in future)
pytest

# lint / format
ruff . && black --check .
```

Memory footprint ≈ 16 MiB RSS (Python + ttkbootstrap) while GUI is open;
`brightness_sync.py` alone uses <10 MiB RSS.

---

## 5. Security Considerations

* Runs entirely as *unprivileged user* after install.
* Access to `/dev/i2c-*` is gated by group membership; installer modifies
  `/etc/group`.
* No DBus, HTTP or network listeners are opened.

---

## 6. Licence

BrightSide is distributed under the **Apache License 2.0**.  See `LICENSE` in
repo root.

---

## 7. Future Work

1. Replace `subprocess` calls with `ctypes` binding to *libddcutil* for near
   instant writes.
2. Add UPower / DBus listener instead of polling `/sys` to remove 50-200 ms
   latency.
3. Flatpak or Snap packaging to avoid the need for a shell installer.
4. GNOME Shell extension (or Quick-Settings tile) that exposes BrightSide
   toggles directly in the desktop UI – no external GUI or systemd setup
   required.
5. Systray / AppIndicator with quick actions: 25 %, 50 %, 75 %, 100 %,
   *mute display* and a toggle for synchroniser on/off.
6. DBus service + CLI tool (`brightctl`) so other scripts can query / set
   brightness without spawning `ddcutil` every time.
7. Integration with GNOME Night-Light schedule – automatically lower external
   monitor brightness after sunset or when *battery saver* kicks in.
8. Per-display presets and automatic profile switching based on
   workspace (office / home) detected through connected Wi-Fi SSID.
9. Wayland secure portal implementation once the **Settings-portal** for
   display configuration is finalised, giving Flatpaks safe access.

