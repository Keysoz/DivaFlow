Diva Store — Windows 11 installer
=================================

This file installs Diva Store on a Windows 11 Pro computer. It does not need
internet access: the Linux environment, Docker Engine, ERPNext and every
container image are inside the installer.

What it does
------------
1. Enables the Windows features WSL2 needs (a restart may be required).
2. Imports a Debian WSL2 distro named `diva-store`.
3. Loads the offline container images.
4. Creates the ERPNext site `diva.local`.
5. Starts the store at http://localhost:8080.
6. Opens the setup wizard, where you enter the company name, abbreviation,
   logo and address. The store then applies its configuration in the
   background.

Requirements
------------
- Windows 11 Pro, 64-bit.
- 8 GB RAM (16 GB recommended), 40 GB free disk.
- Virtualization enabled in the BIOS/UEFI.
- Administrator rights.

First run
---------
Run `DivaStore-Setup-<version>.exe` and accept the prompt, then approve the
Windows Administrator (UAC) prompt. The installer unpacks to `%TEMP%` first and
copies the payload to `C:\DivaStore`, so keep at least 20 GB free. Keep the
window open until it prints the Administrator password. The password is also
saved in:

    C:\DivaStore\ADMIN_PASSWORD.txt

Open http://localhost:8080/login?redirect-to=/diva-setup and sign in as
`Administrator`. The wizard is available only while setup is incomplete.

Everyday commands
-----------------
Run these in an elevated PowerShell from `C:\DivaStore\payload`:

    powershell -ExecutionPolicy Bypass -File install.ps1 -Action Start
    powershell -ExecutionPolicy Bypass -File install.ps1 -Action Stop
    powershell -ExecutionPolicy Bypass -File install.ps1 -Action Status
    powershell -ExecutionPolicy Bypass -File install.ps1 -Action Backup
    powershell -ExecutionPolicy Bypass -File install.ps1 -Action Uninstall

Backups are written to `C:\DivaStore\backups\<timestamp>`.
`-Action Uninstall` deletes the site and its database; it asks for confirmation.

After a Windows restart
-----------------------
The `diva-store` systemd service starts the stack automatically. If the store
does not come back, run `-Action Start`.

WSL2 clock drift
----------------
WSL2 can lose time after sleep. If timestamps look wrong, run:

    wsl -d diva-store -u root -- date -s "<current date and time>"

Troubleshooting
---------------
Installer log: `%TEMP%\diva-install.log`

Container logs:

    wsl -d diva-store -u root -- docker compose -f /opt/diva/store.prod.yml logs --tail 200

Create-site log (first run):

    wsl -d diva-store -u root -- docker compose -f /opt/diva/store.prod.yml logs create-site

Do not edit files inside the containers. Configuration is applied from
`/opt/diva/store.prod.yml` and the Diva config scripts in the backend image.
