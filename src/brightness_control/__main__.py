#!/usr/bin/env python3
"""Package entrypoint – launches the Tkinter/ttkbootstrap app."""

import ttkbootstrap as tb
from .gui import BrightnessApp


def main():
    style = tb.Style("darkly")  # pick a sleek dark theme; change if desired
    root = style.master
    app = BrightnessApp(root)
    root.mainloop()


if __name__ == "__main__":
    main() 