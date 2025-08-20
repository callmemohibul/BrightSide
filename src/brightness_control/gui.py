#!/usr/bin/env python3
"""gui.py – Tkinter application for controlling monitor brightness."""

import sys
from tkinter import Tk, StringVar, messagebox
from typing import Dict

# Use ttkbootstrap for modern themed widgets
import ttkbootstrap as tb
from ttkbootstrap.widgets import ttk

from .controller import BrightnessController, DDCUtilError


class BrightnessApp:
    """Tkinter GUI wrapper."""

    def __init__(self, root: Tk):
        self.root = root
        root.title("Secondary Monitor Brightness Control")
        # Default size
        root.geometry("500x250")
        root.minsize(450, 220)

        # Optional icon (place an 'icon.png' inside the package directory)
        try:
            from tkinter import PhotoImage
            import os, pkg_resources
            icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
            if os.path.exists(icon_path):
                root.iconphoto(False, PhotoImage(file=icon_path))
        except Exception:
            pass  # fallback to default icon

        # Initialise controller
        try:
            self.controller = BrightnessController()
        except DDCUtilError as e:
            messagebox.showerror("ddcutil Error", str(e))
            root.destroy()
            sys.exit(1)

        # Detect monitors
        try:
            self.monitors = self.controller.list_monitors()
        except DDCUtilError as e:
            messagebox.showerror("Detection Error", str(e))
            root.destroy()
            sys.exit(1)

        if not self.monitors:
            messagebox.showinfo("No Monitors", "No DDC-capable monitors were detected.")
            root.destroy()
            sys.exit(0)

        # GUI elements --------------------------------------------------
        self.monitor_var = StringVar(value=list(self.monitors.keys())[0])

        ttk.Label(root, text="Select Monitor:").pack(pady=(10, 0))
        ttk.OptionMenu(root, self.monitor_var, self.monitor_var.get(), *self.monitors.keys(), command=self.on_monitor_change).pack(pady=5)

        ttk.Separator(root, orient="horizontal").pack(fill="x", padx=10, pady=10)

        slider_frame = ttk.Frame(root)
        slider_frame.pack(pady=10)

        # Sun icon label (Unicode ☀)
        ttk.Label(slider_frame, text="\u2600", font=("Helvetica", 14)).grid(row=0, column=0, padx=5)

        self.brightness_var = StringVar(value="0")
        self.slider = ttk.Scale(
            slider_frame,
            from_=0,
            to=100,
            orient="horizontal",
            length=300,
            command=self.on_slider_move,
            bootstyle="warning",  # orange progress bar
        )
        self.slider.grid(row=0, column=1, sticky="ew")

        self.value_label = ttk.Label(slider_frame, textvariable=self.brightness_var, width=4)
        self.value_label.grid(row=0, column=2, padx=5)

        # Status label for inline error/info messages
        self.status_label = ttk.Label(root, text="", foreground="red")
        self.status_label.pack(pady=(5, 0))

        # Bind release event so brightness actually sets
        self.slider.bind("<ButtonRelease-1>", self.on_slider_release)

        # Initialise brightness for default monitor
        self.update_brightness_display()

    # ---------------- Event handlers -----------------
    def on_monitor_change(self, _value):
        self.update_brightness_display()

    def on_slider_move(self, value):
        self.brightness_var.set(str(int(float(value))))

    def on_slider_release(self, _event):
        selected_display = self.monitors[self.monitor_var.get()]
        value = self.slider.get()
        try:
            self.controller.set_brightness(selected_display, value)
        except DDCUtilError as e:
            messagebox.showerror("Set Brightness Error", str(e))

    # ---------------- Helpers ------------------------
    def update_brightness_display(self):
        selected_display = self.monitors[self.monitor_var.get()]
        try:
            brightness = self.controller.get_brightness(selected_display)
            self.status_label.config(text="")
        except DDCUtilError as e:
            # Show status inline instead of disruptive popup
            self.status_label.config(text=str(e), fg="red")
            brightness = 0
        self.slider.set(brightness)
        self.brightness_var.set(str(brightness))

        # Disable slider if unable to read brightness
        if brightness == 0 and self.status_label.cget("text"):
            self.slider.configure(state="disabled")
        else:
            self.slider.configure(state="normal") 