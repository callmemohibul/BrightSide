#!/usr/bin/env python3
"""brightness_sync.py – Mirror GNOME / laptop brightness to external DDC monitors.

This lightweight daemon watches the system back-light brightness value
(usually exposed in /sys/class/backlight/<device>/brightness) and, whenever
it changes, sets the same percentage on every DDC-capable external monitor
found via *ddcutil*.

It is intended to be run as a user-level systemd service so that the
built-in GNOME brightness slider (and laptop Fn keys) controll all screens.

Requirements:
• ddcutil installed and user in the *i2c* group (same as the GUI app).
• Python 3.8+
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from brightness_control.controller import BrightnessController, DDCUtilError

POLL_INTERVAL = 0.005  # seconds

BACKLIGHT_SYSFS_DIR = Path("/sys/class/backlight")


def find_backlight_device() -> Path:
    """Return Path to the backlight directory (defaults to first entry)."""
    candidates = sorted(BACKLIGHT_SYSFS_DIR.iterdir())
    if not candidates:
        raise RuntimeError("No backlight device found under /sys/class/backlight.")
    # Prefer non-virtual devices (e.g. amdgpu_bl1 over acpi_video0)
    preferred = [p for p in candidates if not p.name.startswith("acpi")] or candidates
    return preferred[0]


def read_int(path: Path) -> int:
    return int(path.read_text().strip())


def main() -> None:  # pragma: no cover
    try:
        ctrl = BrightnessController()
    except DDCUtilError as e:
        print(f"[brightness_sync] Fatal: {e}")
        return

    # Detect monitors once on start-up
    try:
        monitors = ctrl.list_monitors()
    except DDCUtilError as e:
        print(f"[brightness_sync] Monitor detection failed: {e}")
        return

    if not monitors:
        print("[brightness_sync] No DDC-capable monitors detected – nothing to sync.")
        return

    backlight = find_backlight_device()
    brightness_file = backlight / "brightness"
    max_file = backlight / "max_brightness"

    max_val = read_int(max_file)
    last_percent: int | None = None

    print(f"[brightness_sync] Watching {brightness_file} (max={max_val}) …")
    print("[brightness_sync] Monitors:")
    for label, num in monitors.items():
        print(f"  • {label} (display {num})")

    while True:
        try:
            current_val = read_int(brightness_file)
        except FileNotFoundError:
            print("[brightness_sync] Brightness file vanished – exiting.")
            return
        percent = int(round((current_val / max_val) * 100))

        if percent != last_percent:
            # Only act on change to reduce ddc traffic
            for display_num in monitors.values():
                try:
                    ctrl.set_brightness(display_num, percent)
                except DDCUtilError as e:
                    print(f"[brightness_sync] Failed to set brightness on display {display_num}: {e}")
            last_percent = percent
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main() 