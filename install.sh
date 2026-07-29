#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=========================================="
echo "  Vortex v2.3 - Full Setup"
echo "=========================================="
echo ""

# --- 1. System dependencies ---
echo "[1/5] Installing system dependencies..."
PACMAN_DEPS=(
    pyside6 python-requests python-psutil python-pyaudio
    wine wine-mono wine-gecko
    python-pip python-pyinstaller
    jdk-openjdk jre-openjdk
    qemu-full swtpm edk2-ovmf dnsmasq
    fuse2 fuse3 unzip p7zip zip tar clamav
)
MISSING=()
for dep in "${PACMAN_DEPS[@]}"; do
    if ! pacman -Qi "$dep" &>/dev/null; then
        MISSING+=("$dep")
    fi
done
if [ ${#MISSING[@]} -gt 0 ]; then
    echo "  -> Installing: ${MISSING[*]}"
    sudo pacman -S --needed --noconfirm "${MISSING[@]}"
else
    echo "  -> All system packages already installed."
fi

# --- 2. Python packages ---
echo ""
echo "[2/5] Installing Python packages..."
python3 -m pip install --user --break-system-packages speechrecognition 2>/dev/null || true

# --- 3. License key ---
echo ""
echo "[3/5] Installing license key..."
cp -n 001235873-KEY "$HOME/" 2>/dev/null || true

# --- 4. Build encrypted binary ---
echo ""
echo "[4/5] Building Vortex binary (AES-encrypted)..."
BUILD_KEY=$(python3 -c "import secrets; print(secrets.token_hex(16))")

pyinstaller --onefile \
    --windowed \
    --name Vortex \
    --key "$BUILD_KEY" \
    --add-data "001235873-KEY:." \
    --add-data "main_stuff:main_stuff" \
    --add-data "other_stuff:other_stuff" \
    --hidden-import PySide6.QtXml \
    --hidden-import PySide6.QtWebEngineWidgets \
    --hidden-import PySide6.QtWebEngineCore \
    --hidden-import requests \
    --hidden-import psutil \
    --hidden-import speech_recognition \
    vortex_app.py 2>&1

if [ ! -f "dist/Vortex" ]; then
    echo "BUILD FAILED!"
    exit 1
fi

echo "  -> Binary built: $(du -h dist/Vortex | cut -f1)"

# --- 5. Install system-wide ---
echo ""
echo "[5/5] Installing system-wide..."
sudo cp dist/Vortex /usr/local/bin/vortex
sudo chmod +x /usr/local/bin/vortex

# Update desktop entry to use the binary
cat > vortex.desktop << 'DESKTOP'
[Desktop Entry]
Name=Vortex
GenericName=Linux Utility Hub
Comment=All-in-one AI, tools, file manager, terminal, code editor, VM, antivirus, modding
Exec=/usr/local/bin/vortex
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=Utility;Development;System;
Keywords=vortex;ai;tools;utility;
StartupWMClass=Vortex
DESKTOP

sudo cp vortex.desktop /usr/share/applications/vortex.desktop
cp vortex.desktop "$HOME/Desktop/Vortex.desktop" 2>/dev/null || true
chmod +x "$HOME/Desktop/Vortex.desktop" 2>/dev/null || true

echo ""
echo "=========================================="
echo "  VORTEX INSTALLED!"
echo "=========================================="
echo "  Binary: /usr/local/bin/vortex"
echo "  Desktop: $HOME/Desktop/Vortex.desktop"
echo "  Menu: Vortex in your app launcher"
echo ""
echo "  Run: vortex"
echo "=========================================="
