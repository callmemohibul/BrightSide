#!/usr/bin/env python3
"""controller.py – handles low-level brightness operations via ddcutil."""

import subprocess
import shutil
import re
from typing import Dict

# Regular expressions for parsing ddcutil output
# Preferred (brief) format: "Display 1: DELL U2415"
DISPLAY_BRIEF_RE = re.compile(r"Display\s+(\d+):\s+(.+)")

# Fallback detailed format
DISPLAY_HEADER_RE = re.compile(r"Display (\d+)")
# Match for full detect output
MODEL_RE = re.compile(r"Model:\s+(.+)")
# Match for brief output blocks
MONITOR_RE = re.compile(r"Monitor:\s+(.+)")

# Brightness line may be decimal or hex (e.g., 0x64)
BRIGHTNESS_RE = re.compile(r"current value =\s*(0x[0-9A-Fa-f]+|\d+)")


class DDCUtilError(Exception):
    """Raised when ddcutil is missing or returns an error."""


class BrightnessController:
    """Encapsulates ddcutil interactions (detect, get, set brightness)."""

    def __init__(self):
        if shutil.which("ddcutil") is None:
            raise DDCUtilError("ddcutil is not installed or not found in PATH.")

    # --------------------------------------------------
    def list_monitors(self) -> Dict[str, int]:
        """Return a mapping of user-friendly label ➔ display number."""
        # Try brief detection first for simpler parsing
        try:
            output = subprocess.check_output(
                ["ddcutil", "detect", "--brief"], text=True, stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as e:
            raise DDCUtilError(f"Failed to detect monitors: {e.output.strip()}") from e

        monitors: Dict[str, int] = {}

        for line in output.splitlines():
            brief_match = DISPLAY_BRIEF_RE.match(line.strip())
            if brief_match:
                display_no = int(brief_match.group(1))
                model = brief_match.group(2).strip()
                monitors[f"Display {display_no}: {model}"] = display_no

        # If brief mode produced results, return them
        if monitors:
            return monitors

        # Fallback to detailed parsing
        current_display = None
        for line in output.splitlines():
            header_match = DISPLAY_HEADER_RE.search(line)
            if header_match:
                current_display = int(header_match.group(1))
                continue
            if current_display is not None:
                model_match = MODEL_RE.search(line) or MONITOR_RE.search(line)
                if model_match:
                    model = model_match.group(1).strip()
                    label = f"Display {current_display}: {model}"
                    monitors[label] = current_display
                    current_display = None  # reset until next header
        return monitors

    # --------------------------------------------------
    def get_brightness(self, display_number: int) -> int:
        """Return current brightness (0-100) for given display number."""
        try:
            output = subprocess.check_output(
                ["ddcutil", "--display", str(display_number), "getvcp", "10"],
                text=True,
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as e:
            raise DDCUtilError(f"Failed to get brightness: {e.output.strip()}") from e

        match = BRIGHTNESS_RE.search(output)
        if not match:
            raise DDCUtilError("Unable to parse brightness from ddcutil output.")
        raw_val = match.group(1)
        if raw_val.lower().startswith("0x"):
            return int(raw_val, 16)
        return int(raw_val)

    # --------------------------------------------------
    def set_brightness(self, display_number: int, value: int | float) -> None:
        """Set brightness to <value> (0-100) for given display number.

        ``ddcutil`` expects an *integer* brightness value.  If callers pass a
        float (e.g. the raw value from a Tkinter ``Scale`` widget), we round
        it to the nearest int to avoid a ``CalledProcessError`` like::

            setvcp 10 58.04195804195804 → exit status 1
        """
        # Ensure we always pass a plain int such as "58" to ddcutil
        int_value = int(round(value))

        try:
            subprocess.check_call(
                [
                    "ddcutil",
                    "--display",
                    str(display_number),
                    "setvcp",
                    "10",
                    str(int_value),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
        except subprocess.CalledProcessError as e:
            raise DDCUtilError(f"Failed to set brightness: {e}") from e 