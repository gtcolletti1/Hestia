#!/usr/bin/env bash
# =============================================================================
# Family Hub — Kiosk Mode Setup
# Sets up a Raspberry Pi or Intel NUC to run Chromium in kiosk mode,
# pointing at the locally-hosted Family Hub dashboard.
# =============================================================================
set -euo pipefail

KIOSK_URL="${KIOSK_URL:-http://localhost}"
SERVICE_FILE="/etc/systemd/system/kiosk.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Family Hub Kiosk Setup ==="
echo "Target URL: ${KIOSK_URL}"
echo ""

# --- 1. Install Chromium browser if not present ---
if ! command -v chromium-browser &>/dev/null && ! command -v chromium &>/dev/null; then
    echo ">> Installing Chromium browser..."
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends chromium-browser || \
        sudo apt-get install -y --no-install-recommends chromium
else
    echo ">> Chromium already installed."
fi

# Resolve the Chromium binary name
CHROMIUM_BIN="$(command -v chromium-browser 2>/dev/null || command -v chromium)"

# --- 2. Install the systemd service ---
echo ">> Installing systemd service..."
if [[ -f "${SCRIPT_DIR}/kiosk.service" ]]; then
    sudo cp "${SCRIPT_DIR}/kiosk.service" "${SERVICE_FILE}"
else
    # Generate inline if the companion file is missing
    sudo tee "${SERVICE_FILE}" > /dev/null <<EOF
[Unit]
Description=Family Hub Kiosk (Chromium)
After=network-online.target graphical.target
Wants=network-online.target

[Service]
Type=simple
User=$(whoami)
Environment=DISPLAY=:0
ExecStart=${CHROMIUM_BIN} \\
    --kiosk \\
    --noerrdialogs \\
    --disable-translate \\
    --no-first-run \\
    --fast \\
    --fast-start \\
    --disable-infobars \\
    --disable-session-crashed-bubble \\
    --disable-component-update \\
    ${KIOSK_URL}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
EOF
fi

sudo systemctl daemon-reload
sudo systemctl enable kiosk.service
echo ">> Kiosk service installed and enabled."

# --- 3. Disable screen blanking / screensaver ---
echo ">> Disabling screen blanking and screensaver..."
# X11 blanking
xset s off        2>/dev/null || true
xset -dpms         2>/dev/null || true
xset s noblank     2>/dev/null || true

# Persist via lightdm config (common on Pi OS)
LIGHTDM_CONF="/etc/lightdm/lightdm.conf"
if [[ -f "${LIGHTDM_CONF}" ]]; then
    if ! grep -q "xserver-command" "${LIGHTDM_CONF}"; then
        sudo sed -i '/^\[Seat:\*\]/a xserver-command=X -s 0 -dpms' "${LIGHTDM_CONF}"
        echo "   Added dpms-off to lightdm.conf"
    fi
fi

# --- 4. Optional: screen sleep / wake schedule ---
echo ">> Setting up display sleep schedule (6 AM on, 10 PM off)..."
CRON_MARKER="# family-hub-display"

# Remove old entries
crontab -l 2>/dev/null | grep -v "${CRON_MARKER}" > /Users/colletti/Projects/family-hub/scripts/_cron_tmp || true

# Detect display control command
if command -v tvservice &>/dev/null; then
    # Raspberry Pi with HDMI
    DISPLAY_OFF="tvservice --off"
    DISPLAY_ON="tvservice --preferred && sudo chvt 6 && sudo chvt 7"
else
    DISPLAY_ON="DISPLAY=:0 xset dpms force on"
    DISPLAY_OFF="DISPLAY=:0 xset dpms force off"
fi

cat >> /Users/colletti/Projects/family-hub/scripts/_cron_tmp <<EOF
0 6 * * * ${DISPLAY_ON}   ${CRON_MARKER}
0 22 * * * ${DISPLAY_OFF}  ${CRON_MARKER}
EOF
crontab /Users/colletti/Projects/family-hub/scripts/_cron_tmp
rm -f /Users/colletti/Projects/family-hub/scripts/_cron_tmp
echo "   Display turns ON at 06:00, OFF at 22:00."

# --- 5. Touch calibration notes ---
# If using a resistive touchscreen, run:
#   sudo apt-get install xinput-calibrator
#   xinput_calibrator
# Then copy the generated calibration data into:
#   /etc/X11/xorg.conf.d/99-calibration.conf
#
# For capacitive screens (most modern ones), calibration is usually
# not required. If touch is rotated, add to /boot/config.txt:
#   lcd_rotate=2
# or use the appropriate display_rotate / dtoverlay settings.

echo ""
echo "=== Setup complete ==="
echo "Start the kiosk now with:  sudo systemctl start kiosk"
echo "View logs with:            journalctl -u kiosk -f"
