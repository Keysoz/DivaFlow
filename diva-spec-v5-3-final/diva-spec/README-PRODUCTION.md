# Diva Store Production Package

This document describes the complete Diva Store package for production deployment on Windows 11 Pro with Docker Desktop/WSL2.

## Package Overview

The Diva Store package includes everything needed to run a complete retail POS system on a Windows PC:

- **ERPNext 16** - Core ERP system
- **Diva Guard** - Server-side validation and business rules
- **Diva Desk** - Frontend desk layer with Arabic localization
- **Custom Reports** - Custom print formats for invoices and receipts
- **POS Next** - Point of Sale system with Arabic support
- **Docker Engine** - Container runtime in WSL2
- **Setup Wizard** - First-time configuration interface
- **Windows Launcher** - Native app shell with WebView2

## Package Structure

```
dist/
├── diva-store-latest.tar.gz         # Docker image archive
├── VERSION                          # Version identifier
├── SHA256SUMS                       # Checksums for verification
├── MANIFEST.txt                     # Package manifest
├── package-info.txt                 # Detailed package information
├── verify-package.sh                # Package verification script
├── README.md                        # Package documentation
├── store.prod.yml                   # Production Docker Compose configuration
├── .env.prod.example                # Environment variables template
├── erpnext-config/                  # ERPNext configuration with placeholders
├── scripts/                         # Installation and configuration scripts
│   ├── install.ps1                  # Windows installer script
│   ├── diva-pos.cmd                 # POS launcher
│   ├── diva-desk.cmd                # Desk launcher
│   ├── build-image.sh               # Docker image builder
│   ├── test-config.sh               # Configuration tester
│   ├── test-setup.sh                # Setup tester
│   └── build-package.sh             # Package builder
└── sources/                         # Source code and licenses
```

## Installation Process

### Windows 11 Pro Installation

1. **Prerequisites**:
   - Windows 11 Pro (64-bit)
   - Enable virtualization in BIOS
   - 16 GB RAM (8 GB minimum)
   - 100 GB free disk space
   - USB drive (16 GB, exFAT)

2. **Copy Package**:
   - Copy the entire `dist` folder to a USB drive

3. **Run Installer**:
   - Insert USB drive into target PC
   - Right-click on PowerShell and select "Run as Administrator"
   - Run `install.ps1` (PowerShell script)
   - Follow the setup wizard

4. **First Run**:
   - The system will start Docker Desktop automatically
   - Follow the prompts to configure your company details
   - Once configured, the POS will open automatically

### Linux Installation

1. **Prerequisites**:
   - Linux distribution with Docker Engine
   - 16 GB RAM (8 GB minimum)
   - 100 GB free disk space

2. **Extract Package**:
   ```bash
   tar -xzf diva-store-latest.tar.gz
   cd dist
   ```

3. **Configure Environment**:
   ```bash
   cp .env.prod.example .env
   # Edit .env with your configuration
   ```

4. **Start the Stack**:
   ```bash
   docker-compose -f store.prod.yml up -d
   ```

5. **Configure Site**:
   ```bash
   bench new-site diva.local
   bench --site diva.local install-app diva_guard
   bench --site diva.local install-app diva_desk
   bench --site diva.local install-app custom_reports
   bench --site diva.local install-app pos_next
   ```

## Configuration

### First-Time Setup

After installation, complete the setup wizard at:
- `http://localhost:8080/diva-setup`

The setup wizard will guide you through:
1. Language selection (Arabic/English)
2. Administrator password
3. Company name and abbreviation
4. Company logo
5. Address, phone, email, website
6. Tax ID
7. User accounts and roles
8. Backup configuration

### Company Profile

After setup, you can modify company details (except name and abbreviation after first transaction) at:
- `http://localhost:8080/desk`
- Navigate to "بيانات الشركة" (Company Profile)

### Daily Operations

#### Starting the System

- On Windows: Double-click the "Diva Store" desktop icon
- The system will start Docker Desktop (if not running) and then the POS

#### Backups

- Backups run automatically nightly
- Manual backup: Right-click tray icon → "نسخ احتياطي الآن"
- Backup location: `D:\Diva\backups` (Windows) or `/home/frappe/frappe-bench/backups` (Linux)

#### Support

- View logs: Right-click tray icon → "السجلات"
- Support bundle: Right-click tray icon → "حزمة الدعم"
- Contact support with the bundle file

## Technical Details

### Architecture

```
Windows 11 22H2+
  ├─ Docker Desktop + WSL2
  │    ├─ Debian distro "diva-store"
  │    │    ├─ Docker Engine CE + compose
  │    │    └─ MariaDB 11.8 + Redis 6.2
  │    └─ ERPNext 16 + Diva apps + POS Next
  └─ Diva Store app (WPF + WebView2)
       ├─ Splash screen
       ├─ POS window
       └─ Tray icon
```

### Data Persistence

- Database: MariaDB in Docker volume
- Redis: Separate volumes for cache, queue, and socketio
- Sites: `/home/frappe/frappe-bench/sites` in Docker volume
- Backups: `D:\Diva\backups` (Windows) or `/home/frappe/frappe-bench/backups` (Linux)

### Networking

- Frontend: `http://localhost:8080`
- Backend: `http://localhost:8000`
- Websocket: `http://localhost:9000`
- All services bound to `127.0.0.1` (no LAN exposure)

### Security

- Company name/abbr frozen after first transaction
- System Manager only can modify company profile
- All changes logged with user information
- Automatic password generation for admin account
- Backup encryption support

## Troubleshooting

### Common Issues

1. **Docker Desktop not starting**:
   - Ensure virtualization is enabled in BIOS
   - Check Windows services for Docker Desktop
   - Restart if needed

2. **POS not loading**:
   - Check if Docker containers are running
   - View logs for errors
   - Try restarting the stack

3. **Printer not working**:
   - Install printer drivers on the host PC
   - Configure printer in ERPNext
   - Test printing from browser first

4. **Setup wizard not accessible**:
   - Ensure ERPNext is running
   - Check if setup is already completed
   - Clear browser cache and try again

### Verification

Run the package verification script:
```bash
cd dist
./verify-package.sh
```

Run the setup tests:
```bash
cd dist
../scripts/test-setup.sh
```

## Updates and Maintenance

### System Updates

1. Download the new package
2. Run the upgrade script: `upgrade.ps1`
3. Follow the prompts
4. Test the system thoroughly

### Backup and Recovery

1. **Daily Backups**: Automatic at 02:00 AM
2. **Manual Backup**: Right-click tray icon → "نسخ احتياطي الآن"
3. **Recovery**: Use `restore.ps1` from the backup

### Performance Monitoring

- Check container health in Docker Desktop
- Monitor backup age in the tray menu
- Review error logs regularly
- Use the support bundle for diagnostics

## Support

### Getting Help

1. **Check Documentation**: See this README and the guides in the package
2. **View Logs**: Right-click tray icon → "السجلات"
3. **Support Bundle**: Right-click tray icon → "حزمة الدعم"
4. **Contact Support**: Email support@diva.com with the bundle file

### Bug Reports

When reporting bugs, include:
- Package version (from VERSION file)
- System information (OS, hardware)
- Error messages and logs
- Steps to reproduce the issue

### Feature Requests

Submit feature requests to:
- Email: features@diva.com
- GitHub: https://github.com/diva/diva-store/issues

## License

This package includes:
- ERPNext (GPLv3)
- POS Next by BrainWise (AGPL-3.0)
- Diva apps (proprietary)

See the `sources/` directory for source code and license details.

## Version History

- v1.0.0: Initial release with complete production package

## Roadmap

- v1.1.0: Enhanced reporting features
- v1.2.0: Multi-location support
- v1.3.0: Mobile app for remote management
- v2.0.0: Cloud-based multi-store management

---

For the latest updates and documentation, visit:
https://diva-store.com/docs