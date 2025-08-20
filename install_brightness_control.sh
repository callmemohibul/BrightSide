#!/usr/bin/env bash
# install_brightness_control.sh
# Installs / updates / uninstalls the Brightness Control GUI on Ubuntu 24.04 LTS

# Exit on error, undefined variable, or pipeline error
set -euo pipefail

APP_DIR="/opt/brightness_control_gui"
VENV_DIR="$APP_DIR/venv"
SCRIPT_NAME="brightness_control_gui.py"
DESKTOP_FILE="/usr/share/applications/brightness_control_gui.desktop"

if [[ $EUID -ne 0 ]]; then
  echo "Please run this script with sudo:" >&2
  echo "  sudo $0" >&2
  exit 1
fi

print_help() {
  cat <<EOF
Usage: sudo $0 [OPTION]

Options:
  -i, install        Install Brightness Control GUI (default behaviour if not installed).
  -u, update         Update an existing installation (same as install if not present).
  -r, uninstall      Remove the application and its desktop entry.
  -h, --help         Show this help message and exit.

If no option is provided, this help text is shown.
EOF
}

# -------------------------------------------------------------
# Map first argument to canonical action keyword
RAW_ARG="${1:-"-h"}"

case "$RAW_ARG" in
  -h|--help) ACTION="-h" ;;
  -i|--install) ACTION="install" ;;
  -u|--update) ACTION="update" ;;
  -r|--uninstall) ACTION="uninstall" ;;
  install|update|uninstall) ACTION="$RAW_ARG" ;;
  *) ACTION="invalid" ;;
esac

# Show help and exit if requested
if [[ "$ACTION" == "-h" ]]; then
  print_help
  exit 0
fi

action_valid() {
  [[ "$1" == "install" || "$1" == "update" || "$1" == "uninstall" ]]
}

if ! action_valid "$ACTION"; then
  echo "Invalid option: $RAW_ARG" >&2
  print_help >&2
  exit 1
fi

# -------------------------------------------------------------
install_or_update() {
  local force=$1   # 0 install, 1 update

  apt update -y
  apt install -y python3 python3-pip python3-venv python3-tk ddcutil rsync

  # -----------------------------------------------------------------
  # Copy application source code to /opt (rsync ensures updates work)
  mkdir -p "$APP_DIR"

  # Sync everything *except* the local .venv or git artefacts
  rsync -a --delete \
    --exclude "*.git*" \
    --exclude "__pycache__/" \
    --exclude ".venv/" \
    "$(dirname "$0")/" "$APP_DIR/"

  # -----------------------------------------------------------------
  # Create / update an isolated virtual-env for the app so that
  # system Python packages remain untouched.
  if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
  fi

  "$VENV_DIR/bin/pip" install --upgrade pip
  if [[ -f "$APP_DIR/requirements.txt" ]]; then
    "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"
  fi

  # Desktop entry (overwrite on update)
  cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Brightness Control GUI
Exec=$VENV_DIR/bin/python $APP_DIR/$SCRIPT_NAME
Icon=display-brightness
Categories=Utility;
StartupNotify=true
Terminal=false
EOF

  # Add user to i2c group if missing (for ddcutil access)
  if ! id -nG "$SUDO_USER" | grep -qw i2c; then
    adduser "$SUDO_USER" i2c
  fi

  echo "\nBrightSide installed to $APP_DIR"
  echo "A dedicated virtual environment has been created at $VENV_DIR."
  echo "Log out/in (or reboot) once to activate i2c permissions if changed."
}

uninstall_app() {
  echo "Removing application files..."
  rm -rf "$APP_DIR"
  rm -f "$DESKTOP_FILE"
  echo "Uninstall complete."
}

# -------------------------------------------------------------
case $ACTION in
  install)
    if [[ -d "$APP_DIR" ]]; then
      echo "An existing installation was found at $APP_DIR."
      read -p "Do you want to update it instead? [y/N]: " ans
      if [[ ${ans,,} == y* ]]; then
        install_or_update 1
      else
        echo "Aborting install."
        exit 0
      fi
    else
      install_or_update 0
    fi
    ;;
  update)
    if [[ ! -d "$APP_DIR" ]]; then
      echo "No existing installation found. Running fresh install instead."
      install_or_update 0
    else
      install_or_update 1
    fi
    ;;
  uninstall)
    if [[ ! -d "$APP_DIR" ]]; then
      echo "Application is not installed. Nothing to do."
      exit 0
    fi
    uninstall_app
    ;;
esac 