# BrightSide  ·  *v0.1* (first public release)

> **NOTE**  
> This is the **first preview release (v0.1)**.  The CLI/DBus API and installer
> are subject to change.  Feedback and bug reports are highly appreciated!

External-monitor brightness control that works **with Ubuntu’s default slider**.

• Mirrors GNOME / Unity / Wayland brightness to any DDC/CI-capable monitor
• Optional themed Tk GUI for manual tweaks
• One-command installer with isolated Python venv under */opt*
• Apache-2.0 licensed, small and hackable

## Quick start
```bash
# clone
git clone https://github.com/yourname/BrightSide.git && cd BrightSide

# install (needs sudo to copy files and add you to the i2c group)
sudo ./install_brightness_control.sh --install
```
Log out/in once so the new *i2c* group membership takes effect. You will then
find **Brightness Control GUI** in your application menu. Enable the
background synchroniser if you want the built-in slider and laptop Fn-keys to
adjust the external screen automatically:
```bash
systemctl --user enable --now brightness-sync.service
```

## Documentation
See the full technical docs in the [`docs/`](docs/) folder.

## Licence
Apache-2.0 – see `LICENSE`. 

## Contributing – we need your ideas!

BrightSide ships with the core synchroniser and a simple GUI.  To make Ubuntu
desktop life even smoother we are looking for **community contributions** such
as:

* GNOME Quick-Settings tile or shell extension
* AppIndicator / Tray popup with preset brightness steps
* `brightctl` CLI & DBus service for scripting
* Night-Light / battery-saver integration
* Auto-profiles per-location (Wi-Fi SSID or dock)

If you’d like to help, fork the repo and open a PR – even small quality-of-life
improvements are welcome.  See `docs/technical.md#future-work` for the full
wishlist. 