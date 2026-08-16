# Alexa-controlled iDotMatrix on Raspberry Pi

This project exposes one local Alexa device named `iDotMatrix`. Alexa turns
that device on or off through a local Fauxmo WeMo emulator; the Pi then uses
the upstream [idotmatrix-api-client](https://github.com/markusressel/idotmatrix-api-client)
over Bluetooth Low Energy.

The project is tested with **Raspberry Pi OS Legacy Bookworm 32-bit** on a
Raspberry Pi Zero W. It expects the normal Raspberry Pi user to be named
`pi`, matching the included systemd unit. Note: Easiest install is via [Raspberry Pi Imager](https://www.raspberrypi.com/software/).

## Runtime behavior

- ON wakes the display, synchronizes its clock, and shows clock style 7 in
  24-hour mode without the date, matching the original `LED_ON.bat`.
- OFF sends the iDotMatrix screen-off command, matching `LED_OFF.bat`.
- Fauxmo acknowledges Alexa immediately. The slower BLE operation runs on a
  single background worker, preventing Alexa's request timeout.
- The requested state is persisted in
  `/opt/idotmatrix-bridge/idotmatrix.state`, so Alexa's follow-up state query
  is answered immediately and the state survives a service restart.

## Requirements

### Hardware and network

- Raspberry Pi Zero W or another Pi with Bluetooth Low Energy.
- Raspberry Pi OS Legacy Bookworm 32-bit (`armhf`).
- The display powered and within BLE range of the Pi.
- The Pi and Echo on the same LAN/subnet. Guest Wi-Fi isolation and some
  routed/VLAN networks block Alexa's local SSDP discovery.
- SSH access and a normal `pi` user with `sudo` access.

### Software installed by the installer

- BlueZ and `bluetooth.service`.
- Python 3.11, `python3-venv`, and `python3-pip`.
- Debian's ARMv6-compatible `python3-dbus-fast` package.
- Debian Pillow and cryptography packages used by the client imports.
- `bleak==0.22.3`, `fauxmo==0.6.0`, and `typing-extensions==4.16.0` in a
  virtual environment.
- The latest source of `idotmatrix-api-client` in
  `/opt/idotmatrix-api-client`.

The upstream package currently declares Python 3.12+, while Legacy Bookworm
32-bit provides Python 3.11. The on/off runtime path works with Python 3.11;
the installer therefore bypasses only the package metadata check and leaves
the upstream source unmodified. Debian's `python3-dbus-fast` is installed
outside the venv and made visible with `--system-site-packages`, avoiding a
long ARMv6 source build.

## Installation from this Git project

Clone this project on the Pi, then run the installer as `pi`:

```sh
cd /tmp
git clone https://github.com/YOUR-ACCOUNT/idot-matrix-pi-alexa.git
cd idot-matrix-pi-alexa
chmod +x install_pi.sh
./install_pi.sh
```

The installer is safe to rerun. It preserves an existing
`/etc/default/idotmatrix-bridge` file and updates the upstream client with
fast-forward-only Git pulls.

## Configure the display

Keep the display powered and visible, then discover its BLE address:

```sh
/opt/idotmatrix-bridge/venv/bin/python \
    /opt/idotmatrix-bridge/bridge.py discover
```

The output is an address such as `64:BA:EB:38:87:7F`. Edit the service
environment file:

```sh
sudo nano /etc/default/idotmatrix-bridge
```

Set these values. Use the actual display size if it is not 64x64:

```ini
IDOTMATRIX_ADDRESS=64:BA:EB:38:87:7F
IDOTMATRIX_SIZE=64x64
IDOTMATRIX_CLOCK_STYLE=7
IDOTMATRIX_LOG_LEVEL=INFO
```

Pinning the address is recommended. Leaving it blank makes each command scan
for the first nearby device whose advertised name starts with `IDM-`.

## Start and verify the service

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now idotmatrix-alexa.service
systemctl is-enabled idotmatrix-alexa.service
systemctl is-active idotmatrix-alexa.service
```

The unit also requires Bluetooth and starts after networking is online. It
restarts automatically if Fauxmo exits unexpectedly.

Inspect logs with:

```sh
sudo journalctl -u idotmatrix-alexa.service -f
```

Test the bridge directly before involving Alexa:

```sh
/opt/idotmatrix-bridge/venv/bin/python \
    /opt/idotmatrix-bridge/bridge.py on

/opt/idotmatrix-bridge/venv/bin/python \
    /opt/idotmatrix-bridge/bridge.py off
```

## Alexa setup

With the service running, say “Alexa, discover devices” or use **Discover
Devices** in the Alexa app. The device appears as `iDotMatrix`.

Use:

- “Alexa, turn on iDotMatrix”
- “Alexa, turn off iDotMatrix”

Fauxmo uses local SSDP discovery, so the Echo and Pi must be able to reach
each other directly on the LAN.

## Files

- `bridge.py`: CLI that invokes the upstream client for `on`, `off`, and
  `discover`.
- `idotmatrixplugin.py`: non-blocking Fauxmo plugin with persisted state.
- `fauxmo.json`: local Alexa device configuration.
- `idotmatrix-alexa.service`: systemd service unit.
- `idotmatrix-bridge.env.example`: non-secret runtime configuration template.
- `requirements-pi.txt`: Python packages installed into the Pi venv.
- `install_pi.sh`: repeatable Pi installation script.
