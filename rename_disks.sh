#!/bin/bash
set -e

echo "=========================================="
echo "  Disk Label Rename"
echo "=========================================="
echo ""
echo "This will rename 3 disks and update mount points:"
echo ""
echo "  sda1: Disc 470        → Disc470"
echo "        /mnt/Disc 470   → /mnt/Disc470"
echo ""
echo "  sdb1: Projects+3DPrint → 3DProjects"
echo "        /mnt/Projects+3DPrint → /mnt/3DProjects"
echo ""
echo "  sdf1: Private Papers   → PrivateDocuments"
echo "        /mnt/Private Papers → /mnt/PrivateDocuments"
echo ""

read -rp "Continue? [y/N]: " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Aborted."
    exit 0
fi

echo ""

# Backup fstab
echo "Backing up /etc/fstab..."
sudo cp /etc/fstab "/etc/fstab.bak.$(date +%Y%m%d%H%M%S)"
echo ""

# --- sda1: Disc 470 → Disc470 ---
echo "----------------------------------------"
echo "[1/3] sda1: Disc 470 → Disc470"
echo "----------------------------------------"

echo "  Unmounting..."
sudo umount /mnt/Disc\ 470 2>/dev/null || sudo umount -l /mnt/Disc\ 470 2>/dev/null || echo "  WARNING: unmount failed"

echo "  Changing label..."
sudo e2label /dev/sda1 Disc470

echo "  Updating fstab..."
sudo sed -i 's|LABEL=Disc\\040470|LABEL=Disc470|g' /etc/fstab
sudo sed -i 's|/mnt/Disc\\040470|/mnt/Disc470|g' /etc/fstab

echo "  Creating mount point..."
sudo mkdir -p /mnt/Disc470

echo "  Mounting..."
sudo mount /mnt/Disc470

if [ -d "/mnt/Disc 470" ] && [ -z "$(ls -A "/mnt/Disc 470" 2>/dev/null)" ]; then
    sudo rmdir "/mnt/Disc 470" 2>/dev/null || true
fi
echo "  Done."
echo ""

# --- sdb1: Projects+3DPrint → 3DProjects ---
echo "----------------------------------------"
echo "[2/3] sdb1: Projects+3DPrint → 3DProjects"
echo "----------------------------------------"

echo "  Unmounting..."
sudo umount /mnt/Projects+3DPrint 2>/dev/null || sudo umount -l /mnt/Projects+3DPrint 2>/dev/null || echo "  WARNING: unmount failed"

echo "  Changing label..."
sudo e2label /dev/sdb1 3DProjects

echo "  Updating fstab..."
sudo sed -i 's|LABEL=Projects+3DPrint|LABEL=3DProjects|g' /etc/fstab
sudo sed -i 's|/mnt/Projects+3DPrint|/mnt/3DProjects|g' /etc/fstab

echo "  Creating mount point..."
sudo mkdir -p /mnt/3DProjects

echo "  Mounting..."
sudo mount /mnt/3DProjects

if [ -d "/mnt/Projects+3DPrint" ] && [ -z "$(ls -A /mnt/Projects+3DPrint 2>/dev/null)" ]; then
    sudo rmdir /mnt/Projects+3DPrint 2>/dev/null || true
fi
echo "  Done."
echo ""

# --- sdf1: Private Papers → PrivateDocuments ---
echo "----------------------------------------"
echo "[3/3] sdf1: Private Papers → PrivateDocuments"
echo "----------------------------------------"

echo "  Unmounting..."
sudo umount /mnt/Private\ Papers 2>/dev/null || sudo umount -l /mnt/Private\ Papers 2>/dev/null || echo "  WARNING: unmount failed"

echo "  Changing label..."
sudo e2label /dev/sdf1 PrivateDocuments

echo "  Updating fstab..."
sudo sed -i 's|LABEL=Private\\040Papers|LABEL=PrivateDocuments|g' /etc/fstab
sudo sed -i 's|/mnt/Private\\040Papers|/mnt/PrivateDocuments|g' /etc/fstab

echo "  Creating mount point..."
sudo mkdir -p /mnt/PrivateDocuments

echo "  Mounting..."
sudo mount /mnt/PrivateDocuments

if [ -d "/mnt/Private Papers" ] && [ -z "$(ls -A "/mnt/Private Papers" 2>/dev/null)" ]; then
    sudo rmdir "/mnt/Private Papers" 2>/dev/null || true
fi
echo "  Done."
echo ""

echo "=========================================="
echo "  All Done!"
echo "=========================================="
echo ""
echo "New fstab:"
grep -v '^#' /etc/fstab | grep -v '^$'
echo ""
echo "Current mounts:"
lsblk -o NAME,LABEL,MOUNTPOINT,SIZE -l 2>/dev/null | grep -v '^[[:space:]]*$'
