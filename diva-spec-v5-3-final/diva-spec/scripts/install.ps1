# Diva Store installer for Windows 11 Pro (DEC-109, PROD-05).
#
# Docker Engine CE runs inside a dedicated Debian WSL2 distro, not Docker
# Desktop. This script imports that distro, loads the offline images, writes the
# secrets, starts the compose stack and opens the setup wizard.
#
# It is safe to run again after a reboot: every step checks what already exists.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File install.ps1
#   powershell -ExecutionPolicy Bypass -File install.ps1 -Action Status
#   powershell -ExecutionPolicy Bypass -File install.ps1 -Action Backup
#   powershell -ExecutionPolicy Bypass -File install.ps1 -Action Uninstall -Force

#Requires -RunAsAdministrator

[CmdletBinding()]
param(
    [ValidateSet("Install", "Start", "Stop", "Backup", "Restore", "Uninstall", "Status")]
    [string]$Action = "Install",
    [string]$PayloadDir = $PSScriptRoot,
    [string]$InstallDir = "C:\DivaStore",
    [string]$Distro = "diva-store",
    [string]$BackupFile = "",
    [switch]$Force,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$script:Distro = $Distro
$script:LogFile = Join-Path $env:TEMP "diva-install.log"
$script:SiteUrl = "http://localhost:8080"
$script:Payload = Join-Path $InstallDir "payload"
$script:EnvFile = Join-Path $InstallDir ".env"
$script:AdminFile = Join-Path $InstallDir "ADMIN_PASSWORD.txt"

function Write-Step {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $line
    Add-Content -Path $script:LogFile -Value $line -Encoding UTF8
}

function Write-Ok {
    param([string]$Message)
    Write-Host "  OK  $Message" -ForegroundColor Green
}

function Fail {
    param([string]$Message)
    Write-Step "ERROR: $Message"
    throw $Message
}

function New-RandomSecret {
    param([int]$Length = 24)
    $alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    $bytes = New-Object byte[] $Length
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    } finally {
        $rng.Dispose()
    }
    $chars = New-Object char[] $Length
    for ($i = 0; $i -lt $Length; $i++) {
        $chars[$i] = $alphabet[$bytes[$i] % $alphabet.Length]
    }
    return -new string($chars)
}

function Get-WslDistros {
    $raw = (& wsl.exe --list --quiet) -join "`n"
    $raw = $raw -replace "`0", ""
    return @($raw -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

function Invoke-Wsl {
    param([string]$Command, [switch]$Quiet)
    if ($Quiet) {
        & wsl.exe -d $script:Distro -u root -- bash -lc $Command *> $null
    } else {
        & wsl.exe -d $script:Distro -u root -- bash -lc $Command | Out-Host
    }
    return $LASTEXITCODE
}

function Invoke-WslChecked {
    param([string]$Command)
    $code = Invoke-Wsl $Command
    if ($code -ne 0) {
        Fail "WSL command failed (exit $code): $Command"
    }
}

function ConvertTo-WslPath {
    param([string]$Path)
    $full = [System.IO.Path]::GetFullPath($Path)
    $drive = $full.Substring(0, 1).ToLowerInvariant()
    $rest = $full.Substring(2).Replace("\", "/")
    return "/mnt/$drive$rest"
}

function Ensure-Directories {
    foreach ($dir in @($InstallDir, $script:Payload, (Join-Path $InstallDir "backups"), (Join-Path $InstallDir "wsl"))) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
        }
    }
}

function Assert-DiskSpace {
    $drive = (Get-Item $InstallDir).PSDrive
    $freeGb = [math]::Round($drive.Free / 1GB, 1)
    if ($freeGb -lt 20) {
        Fail "At least 20 GB free is required on $($drive.Name):; found $freeGb GB."
    }
    Write-Step "Free disk space: $freeGb GB"
}

function Enable-WslFeatures {
    $features = @("Microsoft-Windows-Subsystem-Linux", "VirtualMachinePlatform")
    $needsReboot = $false
    foreach ($name in $features) {
        $feature = Get-WindowsOptionalFeature -Online -FeatureName $name
        if ($feature.State -ne "Enabled") {
            Write-Step "Enabling Windows feature $name..."
            Enable-WindowsOptionalFeature -Online -FeatureName $name -All -NoRestart | Out-Null
            $needsReboot = $true
        }
    }
    if ($needsReboot) {
        Write-Step "A restart is required. Run this installer again after Windows restarts."
        exit 3010
    }
}

function Ensure-Wsl {
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
        Fail "wsl.exe is not available. This installer requires Windows 11 with WSL2."
    }
    Enable-WslFeatures
    $version = (& wsl.exe --status) 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        Write-Step "WSL2 is not ready. Trying 'wsl --install --no-distribution'..."
        & wsl.exe --install --no-distribution
        if ($LASTEXITCODE -ne 0) {
            Fail "WSL2 could not be installed automatically. Install WSL2 from Windows Update, restart, and run this installer again."
        }
        Write-Step "WSL2 installed. Restart Windows and run this installer again."
        exit 3010
    }
    & wsl.exe --set-default-version 2 | Out-Null
}

function Import-Distro {
    $distros = Get-WslDistros
    if ($distros -contains $script:Distro) {
        Write-Step "WSL2 distro '$script:Distro' already exists; resuming."
        return
    }
    $rootfs = Join-Path $script:Payload "rootfs.tar"
    if (-not (Test-Path $rootfs)) {
        Fail "rootfs.tar is missing from $script:Payload. Re-run the installer."
    }
    $target = Join-Path $InstallDir "wsl"
    Write-Step "Importing the Debian WSL2 distro (this can take a few minutes)..."
    & wsl.exe --import $script:Distro $target $rootfs --version 2
    if ($LASTEXITCODE -ne 0) {
        Fail "wsl --import failed with exit code $LASTEXITCODE."
    }
    Write-Ok "Distro imported."
}

function Start-Distro {
    Write-Step "Booting the WSL2 distro..."
    $code = Invoke-Wsl "true"
    if ($code -ne 0) {
        Fail "The WSL2 distro did not start."
    }
    Write-Step "Waiting for Docker Engine..."
    $deadline = (Get-Date).AddMinutes(3)
    while ((Get-Date) -lt $deadline) {
        if ((Invoke-Wsl "docker info" -Quiet) -eq 0) {
            Write-Ok "Docker Engine is running."
            return
        }
        Start-Sleep -Seconds 3
    }
    Fail "Docker Engine did not start inside the WSL2 distro. Check 'wsl -d $script:Distro -u root -- journalctl -u docker'."
}

function Copy-Payload {
    if ([System.IO.Path]::GetFullPath($PayloadDir) -eq [System.IO.Path]::GetFullPath($script:Payload)) {
        Write-Step "Payload already in place."
        return
    }
    $files = @("rootfs.tar", "images.tar", "store.prod.yml", "env.prod.example", "README.txt", "SHA256SUMS")
    foreach ($name in $files) {
        $source = Join-Path $PayloadDir $name
        if (-not (Test-Path $source)) {
            if ($name -eq "SHA256SUMS") { continue }
            Fail "Payload file missing: $source"
        }
        $destination = Join-Path $script:Payload $name
        if ((Test-Path $destination) -and ((Get-Item $destination).Length -eq (Get-Item $source).Length)) {
            continue
        }
        Write-Step "Copying $name to $script:Payload ..."
        Copy-Item -Path $source -Destination $destination -Force
    }
}

function Verify-Payload {
    $manifest = Join-Path $script:Payload "SHA256SUMS"
    if (-not (Test-Path $manifest)) {
        Write-Step "No SHA256SUMS file; skipping checksum verification."
        return
    }
    Write-Step "Verifying payload checksums..."
    foreach ($line in Get-Content $manifest) {
        if (-not $line.Trim()) { continue }
        $parts = $line -split "\s+", 2
        if ($parts.Length -ne 2) { continue }
        $expected = $parts[0].Trim().ToLowerInvariant()
        $name = $parts[1].Trim()
        $path = Join-Path $script:Payload $name
        if (-not (Test-Path $path)) { Fail "Checksummed file missing: $name" }
        $actual = (Get-FileHash -Algorithm SHA256 -Path $path).Hash.ToLowerInvariant()
        if ($actual -ne $expected) {
            Fail "Checksum mismatch for $name. The installer file is corrupt; download it again."
        }
    }
    Write-Ok "Checksums verified."
}

function New-EnvFile {
    if (Test-Path $script:EnvFile) {
        Write-Step "Keeping existing secrets from $script:EnvFile."
        return
    }
    Write-Step "Generating store secrets..."
    $lines = @(
        "# Generated by the Diva Store installer. Keep this file private.",
        "DB_ROOT_PASSWORD=$(New-RandomSecret 28)",
        "REDIS_CACHE_PASSWORD=$(New-RandomSecret 28)",
        "REDIS_QUEUE_PASSWORD=$(New-RandomSecret 28)",
        "ADMIN_PASSWORD=$(New-RandomSecret 16)",
        "HTTP_PORT=8080"
    )
    # Compose reads this file inside Linux; write LF endings so no value ends
    # up with a stray carriage return.
    $text = ($lines -join "`n") + "`n"
    [System.IO.File]::WriteAllText($script:EnvFile, $text, [System.Text.Encoding]::ASCII)
    # Only the Administrator password is shown to the owner.
    $admin = ($lines | Where-Object { $_ -like "ADMIN_PASSWORD=*" }) -replace "^ADMIN_PASSWORD=", ""
    [System.IO.File]::WriteAllText($script:AdminFile, "$admin`n", [System.Text.Encoding]::ASCII)
}

function Protect-Secrets {
    # The .env and the admin password file are the only secrets on disk.
    # Restrict them to the installing user, Administrators and SYSTEM so
    # another local account cannot read the Administrator password.
    $sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    & icacls.exe $script:EnvFile $script:AdminFile /inheritance:r /grant:r "*$sid:F" "*S-1-5-32-544:F" "*S-1-5-18:F" *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Step "Warning: could not restrict permissions on the secret files."
    } else {
        Write-Ok "Secret files restricted to this user and administrators."
    }
}

function Copy-ComposeIntoDistro {
    $wslCompose = ConvertTo-WslPath (Join-Path $script:Payload "store.prod.yml")
    $wslEnv = ConvertTo-WslPath $script:EnvFile
    $wslReadme = ConvertTo-WslPath (Join-Path $script:Payload "README.txt")
    Write-Step "Installing compose file and secrets into the distro..."
    Invoke-WslChecked "mkdir -p /opt/diva && cp '$wslCompose' /opt/diva/store.prod.yml && cp '$wslEnv' /opt/diva/.env && cp '$wslReadme' /opt/diva/README.txt && chmod 600 /opt/diva/.env"
    Write-Ok "Configuration copied."
}

function Load-Images {
    $images = Join-Path $script:Payload "images.tar"
    if (-not (Test-Path $images)) {
        Fail "images.tar is missing from $script:Payload."
    }
    if ((Invoke-Wsl "docker image inspect diva-store:latest mariadb:11.8 redis:6.2-alpine" -Quiet) -eq 0) {
        Write-Step "Container images are already loaded."
        return
    }
    $wslImages = ConvertTo-WslPath $images
    Write-Step "Loading offline container images (this can take several minutes)..."
    Invoke-WslChecked "docker load -i '$wslImages'"
    Write-Ok "Images loaded."
}

function Start-Stack {
    Write-Step "Starting the Diva Store stack..."
    Invoke-WslChecked "cd /opt/diva && docker compose --env-file .env -f store.prod.yml up -d"
    Write-Ok "Stack started."
}

function Wait-ForSite {
    $start = Get-Date
    $deadline = $start.AddMinutes(30)
    Write-Step "Waiting for the site to finish creating (first run takes 5-15 minutes)..."
    $lastReport = $start
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri "$script:SiteUrl/api/method/ping" -TimeoutSec 5
            if ($response.StatusCode -eq 200 -and $response.Content -match "pong") {
                Write-Ok "The site is responding."
                return
            }
        } catch {
            # Not ready yet.
        }
        if (((Get-Date) - $lastReport).TotalMinutes -ge 2) {
            $elapsed = [math]::Round(((Get-Date) - $start).TotalMinutes, 0)
            Write-Step "Still creating the site... ($elapsed minutes elapsed)"
            $lastReport = Get-Date
        }
        Start-Sleep -Seconds 10
    }
    Fail "The site did not respond within 30 minutes. Check logs with: wsl -d $script:Distro -u root -- docker compose -f /opt/diva/store.prod.yml logs create-site"
}

function Show-Credentials {
    $admin = Get-Content $script:AdminFile -ErrorAction SilentlyContinue
    if (-not $admin -and (Test-Path $script:EnvFile)) {
        $admin = (Get-Content $script:EnvFile | Where-Object { $_ -like "ADMIN_PASSWORD=*" }) -replace "^ADMIN_PASSWORD=", ""
        if ($admin) { Set-Content -Path $script:AdminFile -Value $admin -Encoding ASCII }
    }
    Write-Host ""
    Write-Host "Diva Store is ready." -ForegroundColor Green
    Write-Host "  Address:    $script:SiteUrl/diva-setup"
    Write-Host "  Login:      Administrator"
    if ($admin) {
        Write-Host "  Password:   $admin"
        Write-Host "  (also saved in $script:AdminFile)"
    }
    Write-Host ""
    Write-Host "The first page asks for the company name, abbreviation, logo and address."
    Write-Host "After you finish, the store configures itself in the background."
    Write-Host ""
}

function Open-Browser {
    if (-not $NoBrowser) {
        Start-Process "$script:SiteUrl/login?redirect-to=/diva-setup"
    }
}

function Install-Diva {
    Write-Step "Diva Store installer starting."
    Ensure-Directories
    Assert-DiskSpace
    Copy-Payload
    Verify-Payload
    Ensure-Wsl
    Import-Distro
    Start-Distro
    New-EnvFile
    Protect-Secrets
    Copy-ComposeIntoDistro
    Load-Images
    Start-Stack
    Wait-ForSite
    Show-Credentials
    Open-Browser
}

function Start-Diva {
    Start-Distro
    Start-Stack
    Wait-ForSite
    Write-Ok "Diva Store is running at $script:SiteUrl"
}

function Stop-Diva {
    Write-Step "Stopping Diva Store..."
    if ((Get-WslDistros) -contains $script:Distro) {
        Invoke-Wsl "cd /opt/diva && docker compose --env-file .env -f store.prod.yml stop" | Out-Null
    }
    Write-Ok "Diva Store stopped. Data is kept."
}

function Backup-Diva {
    if (-not ((Get-WslDistros) -contains $script:Distro)) {
        Fail "The distro is not installed."
    }
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $target = Join-Path (Join-Path $InstallDir "backups") $stamp
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    Write-Step "Running a database and files backup..."
    Invoke-WslChecked "cd /opt/diva && docker compose --env-file .env -f store.prod.yml exec -T backend bench --site diva.local backup --with-files"
    $wslTarget = ConvertTo-WslPath $target
    Invoke-WslChecked "cd /opt/diva && docker compose --env-file .env -f store.prod.yml cp backend:/home/frappe/frappe-bench/sites/diva.local/private/backups/. '$wslTarget/'"
    Write-Ok "Backup saved to $target"
}

function Restore-Diva {
    if (-not $BackupFile) {
        Fail "Pass -BackupFile <path to a backup folder produced by -Action Backup>."
    }
    if (-not (Test-Path $BackupFile)) {
        Fail "Backup folder not found: $BackupFile"
    }
    $wslSource = ConvertTo-WslPath $BackupFile
    Write-Step "Restoring from $BackupFile ..."
    Invoke-WslChecked "cd /opt/diva && docker compose --env-file .env -f store.prod.yml stop backend frontend websocket scheduler queue-long queue-short"
    Invoke-WslChecked "bash /opt/diva/restore.sh '$wslSource'"
    Invoke-WslChecked "cd /opt/diva && docker compose --env-file .env -f store.prod.yml up -d"
    Write-Ok "Restore finished."
}

function Uninstall-Diva {
    if (-not $Force) {
        $answer = Read-Host "This deletes the site, database and container images. Type DELETE to continue"
        if ($answer -ne "DELETE") {
            Write-Step "Uninstall cancelled."
            return
        }
    }
    Write-Step "Stopping and removing containers and volumes..."
    if ((Get-WslDistros) -contains $script:Distro) {
        Invoke-Wsl "cd /opt/diva && docker compose --env-file .env -f store.prod.yml down -v" | Out-Null
        Write-Step "Unregistering the WSL2 distro..."
        & wsl.exe --terminate $script:Distro | Out-Null
        & wsl.exe --unregister $script:Distro | Out-Null
    }
    Write-Step "Removing installation files..."
    Remove-Item -Recurse -Force $InstallDir -ErrorAction SilentlyContinue
    Write-Ok "Diva Store uninstalled."
}

function Show-Status {
    Write-Step "Diva Store status"
    if (-not ((Get-WslDistros) -contains $script:Distro)) {
        Write-Host "  Distro: not installed"
        return
    }
    Write-Host "  Distro: $script:Distro (installed)"
    $code = Invoke-Wsl "cd /opt/diva && docker compose --env-file .env -f store.prod.yml ps"
    if ($code -ne 0) {
        Write-Host "  Stack: not running"
        return
    }
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "$script:SiteUrl/api/method/ping" -TimeoutSec 5
        Write-Host "  Site:   $script:SiteUrl ($($response.StatusCode))"
    } catch {
        Write-Host "  Site:   not responding"
    }
}

switch ($Action) {
    "Install"   { Install-Diva }
    "Start"     { Start-Diva }
    "Stop"      { Stop-Diva }
    "Backup"    { Backup-Diva }
    "Restore"   { Restore-Diva }
    "Uninstall" { Uninstall-Diva }
    "Status"    { Show-Status }
}
