VORTEX ISO FOLDER
==================
Drop your ISO files here. All ISOs are automatically bootable via QEMU.

YOUR ISOs (already present):
- Windows 11 (8.47 GB): Win11_25H2_English_x64_v2 (1).iso
  Bootable: Yes (UEFI/BIOS bootable)
  For VM: Select in VM Launcher -> Boot VM -> choose UEFI mode for best results
- Arch Linux (1.58 GB): archlinux-2026.07.01-x86_64.iso
  Bootable: Yes (bootable Arch Linux live ISO)
  For VM: Select in VM Launcher -> Boot VM

USAGE:
1. Place .iso files in this folder (or download them)
2. Open Vortex -> ??? VM Launcher -> Scan for ISOs
3. Select ISO -> Boot VM (choose UEFI for Windows 11)
4. Close VM window to save state

NOTES:
- All ISO files are bootable by default (El Torito boot record)
- QEMU uses -boot d (boot from CD-ROM) -> ISOs auto-detect as bootable
- VM disk image: ~/.local/share/vortex/disk.qcow2 (64GB, created on first boot)
- Windows 11 ISO uses UEFI firmware + 4GB RAM by default
