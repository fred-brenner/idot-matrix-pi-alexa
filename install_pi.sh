#!/usr/bin/env bash
set -euo pipefail

# Run this script on the Raspberry Pi as the normal `pi` user:
#   ./install_pi.sh

if [[ "$(id -un)" != "pi" ]]; then
    echo "Run this installer as the pi user, not as root." >&2
    exit 1
fi

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/idotmatrix-bridge"
CLIENT_DIR="/opt/idotmatrix-api-client"
VENV_DIR="${INSTALL_DIR}/venv"

echo "Installing Raspberry Pi OS packages..."
sudo DEBIAN_FRONTEND=noninteractive apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    bluez \
    ca-certificates \
    git \
    python3 \
    python3-cryptography \
    python3-dbus-fast \
    python3-pil \
    python3-pip \
    python3-venv

echo "Enabling Bluetooth..."
sudo systemctl enable --now bluetooth.service

echo "Preparing installation directories..."
sudo install -d -o pi -g pi "${INSTALL_DIR}" "${CLIENT_DIR}"

if [[ -d "${CLIENT_DIR}/.git" ]]; then
    echo "Updating the upstream iDotMatrix client..."
    git -C "${CLIENT_DIR}" pull --ff-only
else
    echo "Cloning the upstream iDotMatrix client..."
    git clone --depth 1 \
        https://github.com/markusressel/idotmatrix-api-client.git \
        "${CLIENT_DIR}"
fi

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    echo "Creating the Python virtual environment..."
    python3 -m venv --system-site-packages "${VENV_DIR}"
fi

echo "Installing Python dependencies..."
"${VENV_DIR}/bin/python" -m pip install --no-cache-dir --no-deps \
    -r "${PROJECT_DIR}/requirements-pi.txt"

# The current upstream project metadata declares Python >=3.12, while the
# Legacy Bookworm 32-bit image provides Python 3.11. The on/off runtime path
# is compatible with Python 3.11, so install the unmodified source while
# bypassing only that metadata check.
"${VENV_DIR}/bin/python" -m pip install --no-cache-dir --no-deps \
    --ignore-requires-python "${CLIENT_DIR}"

echo "Installing bridge files..."
sudo install -o pi -g pi -m 755 \
    "${PROJECT_DIR}/bridge.py" \
    "${PROJECT_DIR}/idotmatrixplugin.py" \
    "${INSTALL_DIR}/"
sudo install -o pi -g pi -m 644 \
    "${PROJECT_DIR}/fauxmo.json" \
    "${INSTALL_DIR}/fauxmo.json"
sudo install -o root -g root -m 644 \
    "${PROJECT_DIR}/idotmatrix-alexa.service" \
    /etc/systemd/system/idotmatrix-alexa.service

if [[ ! -f /etc/default/idotmatrix-bridge ]]; then
    sudo install -o root -g root -m 644 \
        "${PROJECT_DIR}/idotmatrix-bridge.env.example" \
        /etc/default/idotmatrix-bridge
fi

sudo systemctl daemon-reload
sudo systemctl enable idotmatrix-alexa.service

echo
echo "Installation complete. Before starting the Alexa service:"
echo "  1. Discover the display:"
echo "     ${VENV_DIR}/bin/python ${INSTALL_DIR}/bridge.py discover"
echo "  2. Edit /etc/default/idotmatrix-bridge and set IDOTMATRIX_ADDRESS."
echo "  3. Start the service:"
echo "     sudo systemctl restart idotmatrix-alexa.service"
echo "  4. Check it:"
echo "     systemctl --no-pager --full status idotmatrix-alexa.service"
