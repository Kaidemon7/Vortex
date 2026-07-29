#!/usr/bin/env bash
set -Eeuo pipefail

trap 'echo ""; echo "[ERROR] Installation failed on line $LINENO"; exit 1' ERR

clear

echo "=========================================="
echo "      VORTEX ARCH INSTALLER"
echo " Safe Windows + Arch Dual Boot Installer"
echo "=========================================="
echo

if [[ $EUID -ne 0 ]]; then
    echo "Run this script as root."
    exit 1
fi

if [[ ! -d /sys/firmware/efi ]]; then
    echo
    echo "System was not booted in UEFI mode."
    echo "Boot the Arch USB in UEFI mode."
    exit 1
fi

if ! command -v parted >/dev/null; then
    echo "parted is required."
    exit 1
fi

if ! command -v lsblk >/dev/null; then
    echo "lsblk is required."
    exit 1
fi

echo
echo "Detected disks:"
echo

lsblk -d -o NAME,SIZE,MODEL

echo

mapfile -t DISKS < <(
lsblk -dn -o NAME |
while read d
do
    if [[ -b /dev/$d ]]; then
        echo "$d"
    fi
done
)

if [[ ${#DISKS[@]} -eq 0 ]]; then
    echo "No disks found."
    exit 1
fi

if [[ ${#DISKS[@]} -eq 1 ]]; then

    DISK="/dev/${DISKS[0]}"

else

    echo

    for i in "${!DISKS[@]}"
    do
        SIZE=$(lsblk -dn -o SIZE "/dev/${DISKS[$i]}")
        MODEL=$(lsblk -dn -o MODEL "/dev/${DISKS[$i]}")
        echo "$((i+1))) ${DISKS[$i]}  $SIZE  $MODEL"
    done

    echo
    read -rp "Select disk: " PICK

    DISK="/dev/${DISKS[$((PICK-1))]}"

fi

echo
echo "Using disk:"
echo "$DISK"
echo

TABLE=$(parted -ms "$DISK" print | head -2 | tail -1 | cut -d: -f6)

if [[ "$TABLE" != "gpt" ]]; then

    echo
    echo "Disk is not GPT."
    echo "Only GPT is supported."
    exit 1

fi

echo "Current layout:"
echo

lsblk -o NAME,SIZE,FSTYPE,PARTTYPE,MOUNTPOINT "$DISK"

echo

ESP=""

while read -r DEV FSTYPE PTTYPE
do

    if [[ "$FSTYPE" == "vfat" || "$FSTYPE" == "fat32" ]]; then
        ESP="$DEV"
    fi

done < <(
lsblk -ln -o PATH,FSTYPE,PARTTYPE "$DISK"
)

if [[ -z "$ESP" ]]; then

    echo
    echo "No EFI System Partition detected."
    echo "Installer will create one if enough space exists."

else

    echo "EFI Partition:"
    echo "$ESP"

fi

echo

WINDOWS=""

while read -r DEV FS
do

    if [[ "$FS" == "ntfs" ]]; then

        WINDOWS="$DEV"
        break

    fi

done < <(
lsblk -ln -o PATH,FSTYPE "$DISK"
)

if [[ -z "$WINDOWS" ]]; then

    echo
    echo "Windows partition not found."

    read -rp "Continue anyway? (yes/no): " A

    [[ "$A" == "yes" ]] || exit 1

else

    echo "Windows detected:"
    echo "$WINDOWS"

fi

echo
echo
echo "Scanning free space..."
echo

# Find the largest free-space region on the disk
BEST_START=0
BEST_END=0
BEST_SIZE=0

while IFS=: read -r NUM START END SIZE TYPE REST
do
    # Only use free space entries
    [[ "$TYPE" != "free" ]] && continue

    # Remove the sector suffix
    S=${START%s}
    E=${END%s}

    # Calculate size in sectors
    LEN=$((E-S))

    if (( LEN > BEST_SIZE ))
    then
        BEST_SIZE=$LEN
        BEST_START=$S
        BEST_END=$E
    fi

done < <(
    parted -ms "$DISK" unit s print free
)

if (( BEST_SIZE == 0 ))
then
    echo
    echo "No usable free space found."
    echo "parted output:"
    parted -ms "$DISK" unit s print free
    exit 1
fi

# Convert sectors to GB
FREE_GB=$((BEST_SIZE * 512 / 1024 / 1024 / 1024))

echo "Largest free space:"
echo
echo "Start Sector : $BEST_START"
echo "End Sector   : $BEST_END"
echo "Approx Size  : ${FREE_GB} GB"

if (( FREE_GB < 20 ))
then
    echo
    echo "Need at least 20 GB free."
    exit 1
fi

echo
echo "Nothing has been modified yet."

read -rp "Continue? (yes/no): " GO

[[ "$GO" == "yes" ]] || exit 0
echo
echo "======================================"
echo "Creating Linux partitions"
echo "======================================"
echo

SECTOR_SIZE=$(cat /sys/block/$(basename "$DISK")/queue/hw_sector_size)

ESP_SIZE_MB=512
SWAP_SIZE_GB=4

ESP_SECTORS=$((ESP_SIZE_MB*1024*1024/SECTOR_SIZE))
SWAP_SECTORS=$((SWAP_SIZE_GB*1024*1024*1024/SECTOR_SIZE))

CURRENT=$BEST_START

if [[ -z "$ESP" ]]
then

    echo "Creating EFI System Partition..."

    ESP_START=$CURRENT
    ESP_END=$((ESP_START+ESP_SECTORS-1))

    parted -s "$DISK" unit s mkpart ESP fat32 ${ESP_START}s ${ESP_END}s

    partprobe "$DISK"
    udevadm settle

    CURRENT=$((ESP_END+1))

fi

SWAP_START=$((BEST_END-SWAP_SECTORS))

ROOT_START=$CURRENT
ROOT_END=$((SWAP_START-1))

if (( ROOT_END <= ROOT_START ))
then

    echo "Not enough free space."
    exit 1

fi

echo
echo "Partition layout:"
echo

echo "Root : $ROOT_START -> $ROOT_END"

if [[ -z "$ESP" ]]
then
echo "EFI  : $ESP_START -> $ESP_END"
else
echo "EFI  : Existing ($ESP)"
fi

echo "Swap : $SWAP_START -> $BEST_END"

echo

parted -s "$DISK" unit s mkpart ArchRoot ext4 ${ROOT_START}s ${ROOT_END}s

parted -s "$DISK" unit s mkpart ArchSwap linux-swap ${SWAP_START}s 100%

if [[ -z "$ESP" ]]
then

PARTNUM=$(parted -ms "$DISK" print | tail -1 | cut -d: -f1)

parted -s "$DISK" set "$PARTNUM" esp on

fi

partprobe "$DISK"
udevadm settle
sleep 3

ROOT_PART=""
SWAP_PART=""

while read -r DEV LABEL FSTYPE PARTLABEL
do

    if [[ "$PARTLABEL" == "ArchRoot" ]]
    then
        ROOT_PART="$DEV"
    fi

    if [[ "$PARTLABEL" == "ArchSwap" ]]
    then
        SWAP_PART="$DEV"
    fi

done < <(
lsblk -ln -o PATH,LABEL,FSTYPE,PARTLABEL "$DISK"
)

if [[ -z "$ROOT_PART" ]]
then

ROOT_PART=$(blkid | grep ArchRoot | cut -d: -f1)

fi

if [[ -z "$SWAP_PART" ]]
then

SWAP_PART=$(blkid | grep ArchSwap | cut -d: -f1)

fi

if [[ -z "$ESP" ]]
then

ESP=$(lsblk -ln -o PATH,PARTLABEL,FSTYPE |
awk '$2=="ESP"{print $1}')

fi

echo
echo "Detected partitions:"
echo

echo "Root : $ROOT_PART"
echo "Swap : $SWAP_PART"
echo "EFI  : $ESP"

if [[ -z "$ROOT_PART" || -z "$SWAP_PART" || -z "$ESP" ]]
then

echo
echo "Failed to detect one or more partitions."
exit 1

fi

echo
echo "Formatting..."

if [[ ! -b "$ROOT_PART" ]]
then
echo "Root device missing."
exit 1
fi

if [[ ! -b "$SWAP_PART" ]]
then
echo "Swap device missing."
exit 1
fi

mkfs.ext4 -F "$ROOT_PART"

mkswap "$SWAP_PART"

swapon "$SWAP_PART"

if ! blkid "$ESP" | grep -qi vfat
then
mkfs.fat -F32 "$ESP"
fi

echo
echo "Mounting..."

mount "$ROOT_PART" /mnt

mkdir -p /mnt/boot

mkdir -p /mnt/boot/efi

mount "$ESP" /mnt/boot/efi

findmnt /mnt >/dev/null || {
echo "Failed to mount root."
exit 1
}

findmnt /mnt/boot/efi >/dev/null || {
echo "Failed to mount EFI."
exit 1
}

echo
echo "Partitioning complete."
echo
echo "======================================"
echo "Installing Arch Linux"
echo "======================================"
echo

echo "Updating package database..."

pacman -Sy --noconfirm

echo
echo "Installing base packages..."

pacstrap -K /mnt \
base \
linux \
linux-firmware \
base-devel \
grub \
efibootmgr \
os-prober \
networkmanager \
sudo \
nano \
vim \
git \
reflector


if [[ $? -ne 0 ]]
then
    echo
    echo "Pacstrap failed."
    exit 1
fi


echo
echo "Generating fstab..."

genfstab -U /mnt >> /mnt/etc/fstab


if [[ ! -s /mnt/etc/fstab ]]
then

    echo
    echo "fstab generation failed."
    exit 1

fi


echo
echo "fstab created:"
echo

cat /mnt/etc/fstab


echo
echo "Base installation complete."
echo
echo "======================================"
echo "Configuring Arch Linux"
echo "======================================"
echo


arch-chroot /mnt /bin/bash <<'CHROOT'

set -e


echo
echo "Setting timezone..."

ln -sf /usr/share/zoneinfo/UTC /etc/localtime

hwclock --systohc



echo
echo "Configuring locale..."

sed -i 's/^#en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen

locale-gen

echo "LANG=en_US.UTF-8" > /etc/locale.conf



echo
echo "Setting hostname..."

echo "vortex-arch" > /etc/hostname


cat > /etc/hosts <<EOF
127.0.0.1   localhost
::1         localhost
127.0.1.1   vortex-arch.localdomain vortex-arch
EOF



echo
echo "Setting root password..."

passwd



echo
echo "Creating user..."

useradd -m -G wheel -s /bin/bash vortex


echo
echo "Set password for vortex user:"
passwd vortex



echo
echo "Configuring sudo..."

echo "%wheel ALL=(ALL:ALL) ALL" > /etc/sudoers.d/wheel

chmod 440 /etc/sudoers.d/wheel



echo
echo "Enabling services..."

systemctl enable NetworkManager

systemctl enable fstrim.timer



echo
echo "Installing GRUB..."

grub-install \
--target=x86_64-efi \
--efi-directory=/boot/efi \
--bootloader-id=GRUB \
--recheck



echo
echo "Configuring GRUB Windows detection..."

if grep -q "GRUB_DISABLE_OS_PROBER" /etc/default/grub
then

sed -i 's/GRUB_DISABLE_OS_PROBER=.*/GRUB_DISABLE_OS_PROBER=false/' /etc/default/grub

else

echo "GRUB_DISABLE_OS_PROBER=false" >> /etc/default/grub

fi



echo
echo "Generating GRUB menu..."

grub-mkconfig -o /boot/grub/grub.cfg



echo
echo "Arch configuration finished."

CHROOT


if [[ $? -ne 0 ]]
then

echo
echo "Chroot configuration failed."
exit 1

fi


echo
echo "======================================"
echo "Chroot complete"
echo "======================================"
echo
echo "======================================"
echo "Finalizing installation"
echo "======================================"
echo


echo "Checking installed system..."

if [[ ! -f /mnt/etc/fstab ]]
then

    echo "ERROR: fstab missing."
    exit 1

fi


if [[ ! -d /mnt/boot/efi ]]
then

    echo "ERROR: EFI mount missing."
    exit 1

fi


echo
echo "Unmounting filesystems..."

sync


umount -R /mnt || true


echo
echo "Disabling swap..."

swapoff -a || true


echo
echo "Running final disk sync..."

sync


echo
echo "======================================"
echo " INSTALLATION COMPLETE "
echo "======================================"
echo

echo "Your system now contains:"
echo
echo " ✓ Arch Linux installed"
echo " ✓ Windows partitions preserved"
echo " ✓ GRUB bootloader installed"
echo " ✓ Windows Boot Manager detection enabled"
echo " ✓ NetworkManager enabled"
echo
echo "User created:"
echo "  vortex"
echo

echo "Next steps:"
echo
echo "1. Remove the Arch USB."
echo "2. Reboot."
echo "3. Select GRUB from your UEFI boot menu if needed."
echo "4. Choose:"
echo "     Arch Linux"
echo "     Windows Boot Manager"
echo


read -rp "Reboot now? (yes/no): " REBOOT


if [[ "$REBOOT" == "yes" ]]
then

    reboot

else

    echo
    echo "You can reboot manually with:"
    echo
    echo "reboot"

fi