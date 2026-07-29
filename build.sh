#!/usr/bin/env bash
set -e
echo "=========================================="
echo "  Vortex v2.3 - Build Script for Arch Linux"
echo "=========================================="
echo ""

PACKAGES=(
    "python" "python-pip" "python-pyinstaller" "python-pyside6"
    "python-pyside6-webengine" "python-requests" "python-psutil"
    "python-pyaudio" "python-speechrecognition"
    "wine" "wine-mono" "wine-gecko"
    "qemu-full" "dnsmasq" "swtpm" "edk2-ovmf"
    "jdk-openjdk" "jre-openjdk"
    "fuse2" "fuse3"
    "unzip" "p7zip" "zip" "tar"
    "qemu-headless" "virt-viewer"
    "clamav"
    "yay" "base-devel" "git"
)

echo "[*] Checking system dependencies..."
MISSING=()
for dep in "${PACKAGES[@]}"; do
    if ! pacman -Qi "$dep" &>/dev/null; then
        MISSING+=("$dep")
    fi
done
if [ ${#MISSING[@]} -gt 0 ]; then
    echo "[!] Installing missing packages: ${MISSING[*]}"
    sudo pacman -S --needed --noconfirm "${MISSING[@]}"
else
    echo "[*] All system packages already installed."
fi

echo ""
echo "[*] Checking Python packages..."
pip install --user PyInstaller PySide6 PySide6-WebEngine requests psutil speechrecognition pyaudio 2>/dev/null || true

echo ""
echo "[*] Setting up Wine for Windows tools..."
export WINEPREFIX="$HOME/.local/share/vortex/wine"
if [ ! -d "$WINEPREFIX" ]; then
    echo "[*] Creating Wine prefix (this may take a while on first run)..."
    mkdir -p "$WINEPREFIX"
    wineboot --init 2>/dev/null || true
fi

echo ""
echo "[*] Setting up OVMF UEFI variables..."
OVMF_VARS_DIR="$HOME/.local/share/vortex"
mkdir -p "$OVMF_VARS_DIR"
OVMF_VARS="/usr/share/OVMF/OVMF_VARS.fd"
if [ -f "$OVMF_VARS" ] && [ ! -f "$OVMF_VARS_DIR/OVMF_VARS.fd" ]; then
    cp "$OVMF_VARS" "$OVMF_VARS_DIR/OVMF_VARS.fd" 2>/dev/null || true
fi

echo ""
echo "[*] Setting up swtpm for Windows 11 TPM..."
SWTPM_STATE="$HOME/.local/share/vortex/tpm"
mkdir -p "$SWTPM_STATE"

echo ""
echo "[*] Creating Vortex directories..."
mkdir -p "$HOME/Vortex/main_stuff/APK_Tools"
mkdir -p "$HOME/Vortex/main_stuff/IL2CPP_Dumper"
mkdir -p "$HOME/Vortex/main_stuff/UABE"
mkdir -p "$HOME/Vortex/main_stuff/OpenCode"
mkdir -p "$HOME/Vortex/main_stuff/MetaDataEditor"
mkdir -p "$HOME/Vortex/main_stuff/dnSpy"
mkdir -p "$HOME/Vortex/main_stuff/VeraCrypt"
mkdir -p "$HOME/Vortex/main_stuff/.NET"
mkdir -p "$HOME/Vortex/main_stuff/Malwarebytes"
mkdir -p "$HOME/Vortex/main_stuff/Kaid_Gaming"
mkdir -p "$HOME/Vortex/other_stuff/icons"
mkdir -p "$HOME/Vortex/other_stuff/encrypted"
mkdir -p "$HOME/Vortex/other_stuff/isos"
mkdir -p "$HOME/Vortex/other_stuff/launchers"
mkdir -p "$HOME/Vortex/other_stuff/system_backup"
mkdir -p "$HOME/.local/share/vortex/isos"
mkdir -p "$HOME/.local/share/vortex"

echo ""
echo "[*] Setting up license key..."
cp -n "001235873-KEY" "$HOME/Vortex/" 2>/dev/null || true

echo ""
echo "[*] Copying tool files..."
[ -d "main_stuff" ] && cp -r main_stuff/* "$HOME/Vortex/main_stuff/" 2>/dev/null || true
[ -d "other_stuff" ] && cp -r other_stuff/* "$HOME/Vortex/other_stuff/" 2>/dev/null || true

echo ""
echo "[*] Checking for large system tools..."
command -v wine >/dev/null && echo "  [OK] Wine installed" || echo "  [WARN] Wine not found"
command -v qemu-system-x86_64 >/dev/null && echo "  [OK] QEMU installed" || echo "  [WARN] QEMU not found"
command -v qemu-img >/dev/null && echo "  [OK] qemu-img installed" || echo "  [WARN] qemu-img not found"
command -v java >/dev/null && echo "  [OK] Java installed" || echo "  [WARN] Java not found (needed for APKTool/IL2CPP/UABE)"
if [ -f "/usr/share/OVMF/OVMF_CODE.fd" ] || [ -f "/usr/share/qemu/OVMF_CODE.fd" ]; then
    echo "  [OK] OVMF firmware installed"
else
    echo "  [WARN] OVMF firmware not found - Windows 11 VMs need UEFI firmware"
fi
command -v swtpm >/dev/null && echo "  [OK] swtpm (TPM) installed" || echo "  [WARN] swtpm not installed - Windows 11 may require TPM"

echo ""
echo "[*] Building Vortex binary with PyInstaller..."
cd "$(dirname "$0")"

pyinstaller --onefile \
    --windowed \
    --name Vortex \
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

if [ -f "dist/Vortex" ]; then
    echo ""
    echo "=========================================="
    echo "  BUILD SUCCESSFUL!"
    echo "=========================================="
    echo "Binary: $(pwd)/dist/Vortex"
    echo "Size: $(du -h dist/Vortex | cut -f1)"
    echo ""
    echo "Install system-wide:"
    echo "  sudo cp dist/Vortex /usr/local/bin/vortex"
    echo "  sudo chmod +x /usr/local/bin/vortex"
    echo ""
    echo "Desktop entry:"
    echo "  sudo cp vortex.desktop /usr/share/applications/vortex.desktop"
    echo ""
    echo "Run: vortex"
else
    echo "=========================================="
    echo "  BUILD FAILED - check errors above"
    echo "=========================================="
fi