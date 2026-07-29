<#
.SYNOPSIS
    Prepares Windows for Arch Linux dual-boot by shrinking C: partition
.DESCRIPTION
    Run as Administrator in PowerShell. Shrinks Windows partition to make space for Arch Linux.
    After running, reboot to Arch Linux USB and run dualboot_install.sh
#>

# Require Admin
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "Run as Administrator!"
    exit 1
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  VORTEX DUAL-BOOT: WINDOWS PREPARATION" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will shrink your C: drive to make space for Arch Linux."
Write-Host "Recommended: Leave at least 50GB for Arch (more if you want apps/games)."
Write-Host ""

# Get C: drive info
$C = Get-Partition -DriveLetter C
$CSizeGB = [math]::Round($C.Size / 1GB, 1)
$CFreeGB = [math]::Round(($C | Get-Volume).SizeRemaining / 1GB, 1)

Write-Host "Current C: drive: $CSizeGB GB total, $CFreeGB GB free" -ForegroundColor Yellow
Write-Host ""

# Ask for shrink size
$DefaultShrink = [math]::Min(100, [math]::Floor($CFreeGB * 0.5))
Write-Host "How much space to allocate for Arch Linux? (GB)"
Write-Host "  Minimum: 30 GB (base Arch + Vortex)"
Write-Host "  Recommended: 80-150 GB (room for apps, games, VMs)"
Write-Host "  Maximum available: $CFreeGB GB"
$ShrinkGB = Read-Host "Enter size in GB (default: $DefaultShrink)"
if (-not $ShrinkGB) { $ShrinkGB = $DefaultShrink }
$ShrinkGB = [int]$ShrinkGB

if ($ShrinkGB -lt 30) {
    Write-Warning "Less than 30GB may be too small for Arch + Vortex tools."
    $Confirm = Read-Host "Continue anyway? (yes/no)"
    if ($Confirm -ne "yes") { exit 1 }
}

if ($ShrinkGB -gt $CFreeGB) {
    Write-Error "Cannot shrink more than free space ($CFreeGB GB)!"
    exit 1
}

Write-Host ""
Write-Host "Will shrink C: by $ShrinkGB GB" -ForegroundColor Green
Write-Host "New C: size: $([math]::Round($CSizeGB - $ShrinkGB, 1)) GB" -ForegroundColor Green
Write-Host ""
$Confirm = Read-Host "Proceed? (yes/no)"
if ($Confirm -ne "yes") { 
    Write-Host "Cancelled."
    exit 0 
}

Write-Host ""
Write-Host "Shrinking C: partition..." -ForegroundColor Yellow

# Calculate shrink size in bytes
$ShrinkBytes = $ShrinkGB * 1GB

# Use Resize-Partition (correct cmdlet)
try {
    $Partition = Get-Partition -DriveLetter C
    
    # Check max shrinkable size
    $ResizeData = $Partition | Get-PartitionSupportedSize
    $MaxShrink = $ResizeData.SizeMax
    $MaxShrinkGB = [math]::Round($MaxShrink / 1GB, 1)
    
    Write-Host "Maximum shrinkable: $MaxShrinkGB GB" -ForegroundColor Cyan
    
    if ($ShrinkGB -gt $MaxShrinkGB) {
        Write-Error "Cannot shrink by $ShrinkGB GB. Maximum is $MaxShrinkGB GB."
        Write-Host "Try defragmenting C: drive first: defrag C: /U /V" -ForegroundColor Yellow
        exit 1
    }
    
    # Shrink
    $NewSize = $Partition.Size - $ShrinkBytes
    $Partition | Resize-Partition -Size $NewSize -ErrorAction Stop
    
    Write-Host ""
    Write-Host "✅ Successfully shrunk C: by $ShrinkGB GB!" -ForegroundColor Green
    Write-Host ""
    
    # Show new layout
    Write-Host "New partition layout:" -ForegroundColor Cyan
    Get-Partition -DriveLetter C | Format-Table DriveLetter, Size, Type, Offset -AutoSize
    Get-Partition | Where-Object {$_.DriveLetter -eq $null -and $_.Type -ne "Reserved"} | Format-Table DiskNumber, PartitionNumber, Size, Type, Offset -AutoSize
    
} catch {
    Write-Error "Failed to shrink partition: $_"
    Write-Host ""
    Write-Host "Common fixes:" -ForegroundColor Yellow
    Write-Host "  1. Run defrag: defrag C: /U /V" -ForegroundColor Yellow
    Write-Host "  2. Disable hibernation: powercfg /h off" -ForegroundColor Yellow
    Write-Host "  3. Disable page file on C: temporarily" -ForegroundColor Yellow
    Write-Host "  4. Disable System Protection on C:" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  WINDOWS PREPARATION COMPLETE" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Download Arch Linux ISO: https://archlinux.org/download/"
Write-Host "  2. Flash to USB: Rufus (DD mode) or Ventoy"
Write-Host "  3. Boot from USB (UEFI mode!)"
Write-Host "  4. Connect to internet (WiFi: iwctl, Ethernet: auto)"
Write-Host "  5. Run: sudo bash dualboot_install.sh"
Write-Host ""
Write-Host "The unallocated space ($ShrinkGB GB) will be used for Arch Linux." -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANT: Do NOT create new partitions in Windows Disk Management!" -ForegroundColor Red
Write-Host "Let the Arch installer handle partitioning." -ForegroundColor Red
Write-Host ""

# Offer to disable hibernation (helps with dual-boot)
Write-Host "Optional: Disable Windows Fast Startup (recommended for dual-boot)"
$DisableFast = Read-Host "Disable Fast Startup now? (yes/no)"
if ($DisableFast -eq "yes") {
    powercfg /h off
    Write-Host "✅ Hibernation disabled" -ForegroundColor Green
}

# Offer to disable BitLocker if enabled
$BLStatus = manage-bde -status C: | Select-String "Protection On"
if ($BLStatus) {
    Write-Host ""
    Write-Host "BitLocker is ON for C:. Dual-boot may have issues." -ForegroundColor Yellow
    $Decrypt = Read-Host "Suspend BitLocker? (yes/no - you can re-enable after Arch install)"
    if ($Decrypt -eq "yes") {
        manage-bde -protectors -disable C:
        Write-Host "✅ BitLocker suspended" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Reboot to Arch USB when ready." -ForegroundColor Cyan