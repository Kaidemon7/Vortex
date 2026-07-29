VORTEX v2.2 - Linux Utility Hub
=================================
Built for Arch Linux - compiled with PyInstaller

WHAT'S INCLUDED:
26 tabs in the main GUI:
  1. 🤖 AI Chat - Split layout: left sidebar (New Chat, Vortex AI models, OpenCode models, past chat history, delete chat), right side (chat display + input + mic)
  2. 📁 File Manager - Full file browser with copy/move/delete/rename
  3. ⚙️ Task Manager - Process list with kill + open file location
  4. 💻 Code Editor - VS-like IDE: project explorer sidebar (file tree), recent projects, new project wizard (10 languages), build/run (Ctrl+B), syntax highlighting
  5. 🔧 Tools/Modding - 8 sub-tabs (APK, IL2CPP, UABE, Kaid Gaming, MetaData, dnSpy, VeraCrypt, .NET, System Apps)
  6. ⌨️ Terminal - Run commands + install <url> + auto-scan downloads
  7. 📊 System Info - OS, CPU, RAM, disk, network, uptime
  8. 🌐 Browser - Embedded web browser (Google/DDG/Bing/Opera/Brave) + browser guard (blocks malicious TLDs: .xyz, .tk, .ml, .ga, .cf, .gq, .click, .stream, .date, .faith, .party, .loan, .racing, .win, .bet, .gift, .link, .site, .online, .top, .pw, .buzz, .cricket, .download, .gdn, .pro, .review, .surf, .tkf, .vn + suspicious domains)
  9. 🖥️ VM Launcher - Boot Windows 11 / Linux ISOs with QEMU/KVM (all ISOs auto-bootable via El Torito). Windows 11 auto-detected → UEFI (OVMF) + TPM 2.0 (swtpm) mode.
  10. 🔒 Encryption - AES/XOR file encrypt/decrypt (copy mode, keeps originals)
  11. 🎨 Icon Customizer - Drag PNGs onto system icons, right-click to revert (real system-level GTK theme replacement with backup/restore)
  12. 🎮 PlayFab - Enter Title ID + Secret Key, query cloud scripts, admin panel
  13. 🛡️ Security - Antivirus scanner (ClamAV + custom signatures), firewall (UFW), browser guard (URL reputation check with expanded malicious TLD/domains blocklist), ScreenConnect/AnyDesk/TeamViewer blocker
  14. 💬 Discord - Launch Discord app or web version
  15. 🎯 Unity - Scan for Unity projects on your system
  16. 💿 ISO Tools - Download ISOs + USB writer + bootable VM support (ISO folder auto-created)
  17. 💾 Backup - System file backup (configs, packages, GRUB)
  18. ⚠️ WIPE - Type "wipe" 3x, confirm 3x (ACTUALLY DELETES FILES - preserves encrypted folder only)
  19. 💎 Kaid Gaming - HTML viewer with Kaid Gaming content
  20. 📊 System Specs - Detailed hardware info (OS, CPU model/cores, RAM slots/speed, disk partitions/usage, WiFi/SSID/signal, GPU)
  21. 🎮 OpenCode Launcher - Launch OpenCode Desktop IDE from main_stuff/
  22. 📝 MetaData Editor - Launch MetaData String Editor for IL2CPP dumps
  23. 🎯 Unity Hub Installer - Install Unity Hub (AUR) + manage Editor versions via Hub
  24. 💬 Discord Installer - Install Discord from Arch repos or Flatpak
  25. 🤖 Android Studio Installer - Install Android Studio (AUR/Flatpak) + SDK Manager
  26. 🎮 Creative Apps - Install Blender, Krita, Godot, Heroic (Epic), VS Code, Java JDK from Arch repos

Tools inside main_stuff/:
- APK_Tools - APKTool GUI, apksigner, aapt, zipalign, smali (53 MB)
- IL2CPP_Dumper - Unity IL2CPP game dumper (25 MB)
- UABE - Asset Bundle Editor (classic + .NET/Avalonia version) (41 MB)
- MetaDataEditor - MetaData String Editor (0.2 MB)
- dnSpy - .NET decompiler (zipped)
- VeraCrypt - Disk encryption (AppImage, 13 MB)
- .NET - .NET 6.0 Windows runtime + Linux install instructions (55 MB)
- Malwarebytes - Malwarebytes installer for Windows (2.9 MB)
- OpenCode - OpenCode Desktop IDE (474 MB, 148 files)
- Kaid_Gaming - Your Kaid Gaming files

INSTALLATION ON ARCH LINUX:
1. Copy the Vortex folder to your Linux machine
2. Run the build script (installs ALL dependencies automatically):
     cd Vortex
     chmod +x build.sh
     sudo ./build.sh
   Or install manually:
     sudo pacman -S python python-pip python-pyinstaller python-pyside6
     python-pyside6-webengine python-requests python-psutil
     python-pyaudio python-speechrecognition
     wine wine-mono wine-gecko
     qemu-full qemu-headless swtpm edk2-ovmf dnsmasq
     jdk-openjdk jre-openjdk fuse2 fuse3 p7zip unzip clamav
3. Build the binary:
   ./build.sh
4. Install system-wide:
   sudo cp dist/Vortex /usr/local/bin/vortex
   sudo cp vortex.desktop /usr/share/applications/
5. Run: vortex

WINDOWS TOOLS ON LINUX:
All Windows tools run via Wine:
- APKTool, IL2CPP Dumper, UABE → need Java JDK
- MetaData Editor, dnSpy → need .NET (via Wine)
- VeraCrypt → needs FUSE/fuse2 installed
Wine auto-installs on first run via build.sh.
Install Java: sudo pacman -S jdk-openjdk jre-openjdk
Install OVMF (UEFI for VMs): sudo pacman -S edk2-ovmf
Install TPM (Windows 11 VMs): sudo pacman -S swtpm

AUTO-DOWNLOAD MISSING APPS:
When you click a missing app in Tools or System Apps, Vortex will auto-detect
the absence and offer to install it via pacman (for tools with Arch Linux packages).
For tools without Arch packages, Vortex shows where to download them.

VORTEX AI:
- The AI Chat tab now has an OpenCode-style split layout:
  - LEFT SIDEBAR: "+ New Chat" button, model selectors (Vortex AI + OpenCode), past chat history list, "Delete Selected Chat" button
  - RIGHT SIDE: Chat display with scrollback, input field + Mic + Send button
- Click any past chat in the sidebar to reload it
- Chat titles auto-update based on your first message
- Your OpenRouter key is used for both Vortex AI and OpenCode models
- Models: Vortex AI (GPT-4o, GPT-4o-mini, Claude-3.5-Sonnet, Llama-3.3-70B, Mixtral-8x7B) + OpenCode Style (Llama-3.3-70B, Mixtral-8x7B)

VM LAUNCHER:
Boot Windows 11 / Linux ISOs with QEMU/KVM. All ISOs auto-bootable (El Torito).
Windows 11: Auto-detected → UEFI (OVMF) + TPM 2.0 (swtpm) mode.
Place ISOs in: ~/Vortex/other_stuff/isos/
Windows 11 ISO: https://www.microsoft.com/software-download/windows11
Linux ISOs: Any official .iso from ubuntu.com, linuxmint.com, archlinux.org, etc.
Install: sudo pacman -S qemu-full swtpm edk2-ovmf
VM disk: ~/.local/share/vortex/disk.qcow2 (64GB, auto-created)

SCREENCONNECT BLOCKER:
Vortex blocks common remote access domains at the /etc/hosts level.
Blocked: update.tap-vpns.top, screenconnect.com, anydesk.com, teamviewer.com

BROWSER GUARD (Security + Browser tabs):
- Checks URLs against expanded malicious TLD blocklist (30+ TLDs)
- Blocks suspicious domains (duckdns.org, ngrok.io, serveo.net, crack/keygen/hack/warez/torrent sites)
- Warns on non-HTTPS connections
- Fetches page content to scan for malware terms

CODE EDITOR (VS-LIKE FEATURES):
- Project explorer sidebar with file tree (click to open files)
- Recent projects dropdown
- New project wizard (Python, HTML, JS, C, C++, Java, Go, Rust, JSON, Text)
- Build/run with Ctrl+B (syntax check for Python, compile for C/C++/Java/Rust/Go)
- Syntax highlighting (Python, C/C++, JS, HTML, Java, Rust, Go, JSON, etc.)
- Multi-tab editor with line numbers

DUAL-BOOT INSTALLER (dualboot_install.sh):
Run on Arch ISO to install Arch Linux + Windows dual-boot on single SSD:
- Detects SSD, partitions for EFI/Windows/Arch/swap
- Installs base Arch + linux + linux-firmware + grub + efibootmgr + networkmanager + intel-ucode/amd-ucode
- Configures GRUB with Windows detection
- Enables TRIM (fstrim.timer), networkmanager, reflector.timer
- Adds Vortex auto-install command
- Run: sudo bash dualboot_install.sh

ISO BOOTABILITY:
All ISOs in ~/Vortex/other_stuff/isos/ are bootable in QEMU via -boot d.
Win11 ISO (8.5GB) and Arch ISO (1.6GB) already present on your Desktop.

LARGE APPS (not bundled, install via dedicated installer tabs):
Unity Hub → Tab "🎯 Unity Hub Installer" → Installs from AUR, then manages Editor versions
Discord → Tab "💬 Discord Installer" → Installs from Arch repos or Flatpak
Android Studio → Tab "🤖 Android Studio Installer" → Installs from AUR/Flatpak + SDK
Epic Games → Tab "🎮 Creative Apps" → Heroic Games Launcher (native Linux Epic client)
Blender → Tab "🎮 Creative Apps" → sudo pacman -S blender
Krita → Tab "🎮 Creative Apps" → sudo pacman -S krita
Godot → Tab "🎮 Creative Apps" → sudo pacman -S godot
VS Code → Tab "🎮 Creative Apps" → sudo pacman -S code
Java JDK → Tab "🎮 Creative Apps" → sudo pacman -S jdk-openjdk

LICENSE KEY:
001235873-KEY must be present on system for features to work.

SECURITY NOTE:
OpenRouter API key in source was exposed - REVOKE IT at https://openrouter.ai/keys
Generate a new one and replace OPENROUTER_API_KEY in vortex_app.py line 59.

BUILD.SCRIPT:
Comprehensive build.sh installs all dependencies, compiles with PyInstaller (--onefile --noconsole),
creates vortex.desktop, and outputs dist/Vortex binary (~100-150MB).

RUNNING FROM SOURCE (no compile):
python vortex_app.py