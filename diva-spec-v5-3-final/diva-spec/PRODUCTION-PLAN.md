# Diva Store Production Plan

## Overview

This document outlines the complete production plan for Diva Store, a retail POS system built on ERPNext 16 with Arabic localization and custom business rules.

## Architecture

### System Architecture
```
Windows 11 Pro PC
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

### Data Flow
1. User interacts with WPF app (WebView2 container)
2. App communicates with ERPNext at `http://localhost:8080`
3. ERPNext processes through Diva Guard for business rules
4. Data stored in MariaDB with Redis for caching
5. POS Next handles offline functionality via service worker

## Package Components

### Core Package
- **Docker Image**: ERPNext 16 + Diva apps + POS Next (baked)
- **Docker Compose**: Production configuration with health checks
- **WSL2 Distro**: Debian + Docker Engine (redistributable)
- **Setup Scripts**: Windows installer with resume capability
- **WPF App**: Native shell with WebView2

### Configuration
- **Parameterized Config**: `{company}`/`{abbr}` placeholders
- **Company Profile**: Web-based setup wizard and management
- **Print Formats**: Custom invoices, receipts, and statements
- **User Management**: Role-based access control

### Data Management
- **Fresh Site**: No synthetic data imported to production
- **Master Import**: Only real customers/suppliers/items
- **Opening Balances**: Stock, AR, AP, cash at go-live
- **Backups**: Nightly with external copy

## Implementation Plan

### Phase 1: Core Infrastructure (PROD-01 to PROD-03)
1. **Pinned Image**: Build Docker image with all apps baked in
2. **Production Compose**: Health checks, restart policies, no defaults
3. **Image Archive**: Distributable tar with checksums

### Phase 2: Configuration (PROD-19 to PROD-24)
1. **Company Profile API**: Safe field updates, freeze guard
2. **Setup Wizard**: Web-based first-time configuration
3. **Parameterized Config**: Replace hardcoded values
4. **Print Formats**: Use company name/logo/address

### Phase 3: Windows Package (PROD-04 to PROD-10)
1. **WSL Distro**: Docker Engine in Debian
2. **Windows Installer**: PowerShell script with resume
3. **WPF App**: Native shell with splash and tray
4. **Shortcuts**: POS and Desk launchers
5. **Backups**: Scheduled with external copy
6. **Doctor**: System health check

### Phase 4: Data and Go-Live (PROD-11 to PROD-15)
1. **Master Export**: From dev to review sheet
2. **Fresh Site**: No synthetic data
3. **Import**: Only real masters
4. **Opening Balances**: At go-live
5. **Acceptance**: Full test and restore drill

## Technical Specifications

### Hardware Requirements
- **CPU**: i5/Ryzen 5 or equivalent
- **RAM**: 16 GB (8 GB minimum)
- **Storage**: 100 GB SSD
- **Network**: Wired Ethernet
- **Power**: UPS 650-1000 VA

### Software Requirements
- **OS**: Windows 11 Pro (64-bit)
- **Virtualization**: Enabled in BIOS
- **Docker**: Docker Engine CE in WSL2
- **Browser**: Edge (WebView2)

### Security
- **Company Name/Abbr**: Frozen after first transaction
- **Access Control**: System Manager only for company profile
- **Audit Logging**: All changes logged
- **Backups**: Encrypted, off-site copies

## Deployment Process

### Installation
1. Copy `dist` folder to USB drive
2. Run `install.ps1` on target PC
3. Follow setup wizard
4. Complete company configuration
5. Launch POS

### Daily Operations
1. Power on PC
2. Double-click "Diva Store" icon
3. POS opens automatically
4. Work as normal
5. Nightly backups run automatically

### Maintenance
1. Quarterly updates via new USB
2. Backup verification monthly
3. System health checks weekly
4. User management as needed

## Testing Strategy

### Unit Tests
- Configuration parameterization
- Company profile API
- Print format generation
- User creation

### Integration Tests
- Docker image build and run
- WSL2 distro import
- Setup wizard flow
- Backup and restore

### Acceptance Tests
- Full installation on VM
- Complete sales cycle
- Arabic functionality
- Receipt printing
- Offline mode

## Risk Mitigation

### Technical Risks
- **WSL2 Clock Drift**: Disable sleep, supervisor restarts on resume
- **Docker Updates**: Pin version, disable auto-update
- **Data Corruption**: Regular backups, verify integrity
- **Performance**: Monitor resources, scale as needed

### Business Risks
- **Data Loss**: Regular backups, off-site copies
- **Downtime**: UPS, automatic restart
- **User Error**: Clear UI, confirmation dialogs
- **Compliance**: Audit logs, access controls

## Support and Maintenance

### Support Channels
- **Documentation**: Comprehensive guides and troubleshooting
- **Remote Support**: TeamViewer access with logs
- **Local Support**: On-site visits for critical issues
- **Community**: Forum for peer support

### Maintenance Schedule
- **Daily**: Check backup status
- **Weekly**: System health check
- **Monthly**: Full restore test
- **Quarterly**: System update

## Success Metrics

### Operational Metrics
- **Uptime**: >99.5%
- **Response Time**: <2 seconds
- **Backup Success**: 100%
- **Error Rate**: <0.1%

### Business Metrics
- **Sales Throughput**: Transactions per hour
- **User Satisfaction**: Monthly surveys
- **System Reliability**: Downtime incidents
- **Data Accuracy**: Reconciliation results

## Timeline

### Phase 1 (2 weeks)
- Docker image and compose
- Package build scripts

### Phase 2 (1 week)
- Company profile API
- Setup wizard
- Parameterized config

### Phase 3 (2 weeks)
- WSL2 distro
- Windows installer
- WPF app

### Phase 4 (1 week)
- Data migration
- Acceptance testing
- Documentation

## Budget

### Development
- **Infrastructure**: $5,000
- **Development**: $20,000
- **Testing**: $5,000
- **Documentation**: $3,000

### Deployment
- **Hardware**: $1,000 per site
- **Installation**: $500 per site
- **Training**: $1,000 per site

### Maintenance
- **Annual Support**: $3,000 per site
- **Updates**: $1,000 per year
- **Backup Storage**: $500 per year

## Conclusion

Diva Store provides a complete, production-ready POS solution for retail businesses with Arabic language support. The package includes everything needed for installation, configuration, and daily operations, with comprehensive documentation and support.

The architecture ensures reliability, security, and scalability while maintaining ease of use for non-technical staff. The parameterized configuration allows for easy customization for different businesses, while the frozen company name/abbr ensures data integrity.

With proper implementation and maintenance, Diva Store can serve as the core POS system for retail businesses of all sizes.