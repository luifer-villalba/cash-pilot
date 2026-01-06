# CashPilot Documentation Index

Welcome to the CashPilot documentation. This index helps you find the right documentation for your needs.

**Last Updated:** 2025-01-29

---

## 📚 Quick Navigation

### For New Developers
1. Start with [Main README](../README.md) - Project overview and quick start
2. Read [Architecture Overview](#architecture) - Understand the system design
3. Review [Local Setup Guide](#development) - Get running locally
4. Explore [Code Map](#architecture) - Find where functionality lives

### For Maintainers
1. [Deployment Guide](#deployment) - Railway-specific deployment steps
2. [Troubleshooting](#development) - Common issues and solutions
3. [Windows 7 Compatibility](#development) - Legacy browser support
4. [Security Policy](../SECURITY.md) - Security practices and vulnerability management

### For Contributors
1. [Contributing Guide](../CONTRIBUTING.md) - Contribution guidelines
2. [Design System](design_readme.md) - UI/UX patterns and component guidelines
3. [API Reference](#architecture) - Endpoint documentation

---

## 📖 Documentation by Category

### 🏗️ Architecture & Design

#### [Design System Guide](design_readme.md)
**Purpose:** Complete UI/UX design system and component patterns  
**Audience:** Frontend developers, designers  
**Last Updated:** 2025-01-29  
**Content:**
- Tailwind CSS + DaisyUI patterns
- Form components and validation
- HTMX interaction patterns
- Accessibility requirements
- Report page patterns

#### [Architecture Decisions](architecture-decisions.md)
**Purpose:** Document why key technical decisions were made  
**Audience:** Developers, architects  
**Last Updated:** 2025-01-29  
**Content:**
- 10 ADRs documented (FastAPI, server-rendered, session auth, etc.)
- Rationale and alternatives for each decision
- Template for future ADRs

#### Data Model (Coming Soon)
**Purpose:** Visual database schema with relationship explanations  
**Status:** To be created  
**Planned Content:**
- Entity-relationship diagrams
- Table descriptions
- Foreign key relationships
- Indexes and constraints
- Timezone handling

#### Code Map (Coming Soon)
**Purpose:** "Where to find X functionality" guide  
**Status:** To be created  
**Planned Content:**
- Feature → file mapping
- Business logic locations
- Authentication flow
- Session lifecycle code paths

---

### 🛠️ Development

#### [Windows 7 Compatibility Guide](w7-compatibility.md)
**Purpose:** Comprehensive guide to legacy browser support  
**Audience:** Frontend developers  
**Last Updated:** 2025-01-29  
**Content:**
- CSS fallback patterns
- JavaScript polyfills
- Build configuration
- Testing checklist
- Common issues and fixes

#### Local Setup Guide (Coming Soon)
**Purpose:** Step-by-step local development setup with troubleshooting  
**Status:** To be created  
**Planned Content:**
- Prerequisites
- Installation steps
- Environment variables
- Database setup
- Running tests
- Common gotchas

#### Troubleshooting Guide (Coming Soon)
**Purpose:** Common issues and their solutions  
**Status:** To be created  
**Planned Content:**
- Database connection issues
- Migration problems
- Static file serving
- Authentication issues
- Performance debugging

---

### 🚀 Deployment

#### [Backup & Restore Guide](backup_restore.md)
**Purpose:** Database backup and restore procedures for Railway  
**Audience:** DevOps, maintainers  
**Last Updated:** 2025-01-29  
**Content:**
- Backup scripts overview
- Restore procedures
- Testing backups locally
- Railway-specific instructions
- Security notes

#### Railway Deployment Guide (Coming Soon)
**Purpose:** Step-by-step Railway deployment instructions  
**Status:** To be created  
**Planned Content:**
- Railway account setup
- Environment configuration
- Database provisioning
- Auto-deploy setup
- Monitoring and logs

#### Environment Configuration (Coming Soon)
**Purpose:** Complete environment variable reference  
**Status:** To be created  
**Planned Content:**
- Required variables
- Optional variables
- Development vs production
- Security best practices

---

### 📊 Business & Analytics

#### [Business Statistics Audit](business_stats_audit.md)
**Purpose:** Comprehensive audit of business statistics report  
**Audience:** Developers, QA  
**Last Updated:** 2025-01-29  
**Content:**
- Critical issues found
- Calculation bugs
- Edge cases
- Testing recommendations
- Fix priorities

#### Business Context (Coming Soon)
**Purpose:** Problem space, user stories, and business requirements  
**Status:** To be created  
**Planned Content:**
- Problem statement
- User personas
- Key workflows
- Acceptance criteria
- Future enhancements

---

### 🔒 Security

#### [Security Policy](../SECURITY.md)
**Purpose:** Security practices, vulnerability reporting, and CVE tracking  
**Audience:** All contributors  
**Last Updated:** 2025-01-29  
**Content:**
- Security audit process
- Vulnerability severity levels
- Resolved CVEs
- False positives tracking
- Reporting process

---

## 📋 Recommended Reading Paths

### Path 1: New Developer Onboarding (30 minutes)
1. [Main README](../README.md) - 5 min
2. [Design System Guide](design_readme.md) - 10 min (skim patterns)
3. [Windows 7 Compatibility](w7-compatibility.md) - 5 min (awareness)
4. [Backup & Restore](backup_restore.md) - 5 min (awareness)
5. Explore codebase with [Code Map](#) - 5 min (when available)

### Path 2: Frontend Developer
1. [Design System Guide](design_readme.md) - Complete read
2. [Windows 7 Compatibility](w7-compatibility.md) - Complete read
3. Review `templates/` directory structure
4. Review `static/css/input.css` and `static/js/` files

### Path 3: Backend Developer
1. [Main README](../README.md) - Architecture section
2. [Architecture Decisions](#) - When available
3. [Data Model](#) - When available
4. Review `src/cashpilot/` directory structure
5. Review `tests/` for API patterns

### Path 4: DevOps/Maintainer
1. [Backup & Restore Guide](backup_restore.md) - Complete read
2. [Railway Deployment Guide](#) - When available
3. [Environment Configuration](#) - When available
4. [Security Policy](../SECURITY.md) - Complete read

### Path 5: Contributor
1. [Contributing Guide](../CONTRIBUTING.md)
2. [Design System Guide](design_readme.md) - Relevant sections
3. [Windows 7 Compatibility](w7-compatibility.md) - If touching frontend
4. Review existing code patterns before contributing

---

## 🔍 Finding Specific Information

### "How do I...?"

| Question | Document |
|----------|----------|
| Set up local development? | [Local Setup Guide](#) (coming soon) |
| Deploy to Railway? | [Railway Deployment Guide](#) (coming soon) |
| Add a new form component? | [Design System Guide](design_readme.md) |
| Ensure Windows 7 compatibility? | [Windows 7 Compatibility](w7-compatibility.md) |
| Backup the database? | [Backup & Restore Guide](backup_restore.md) |
| Report a security issue? | [Security Policy](../SECURITY.md) |
| Understand the data model? | [Data Model](#) (coming soon) |
| Find where X feature is implemented? | [Code Map](#) (coming soon) |

### "What is...?"

| Concept | Document |
|---------|----------|
| The architecture? | [Main README](../README.md) + [Architecture Decisions](#) |
| The design system? | [Design System Guide](design_readme.md) |
| The database schema? | [Data Model](#) (coming soon) |
| The deployment process? | [Railway Deployment Guide](#) (coming soon) |
| The security process? | [Security Policy](../SECURITY.md) |

---

## 📝 Documentation Status

### ✅ Complete & Current
- [x] Main README
- [x] Design System Guide
- [x] Windows 7 Compatibility Guide
- [x] Backup & Restore Guide
- [x] Business Statistics Audit
- [x] Security Policy
- [x] Architecture Decisions
- [x] Documentation Index (this file)

### 🚧 In Progress
- [ ] Data Model
- [ ] Code Map
- [ ] Local Setup Guide
- [ ] Troubleshooting Guide
- [ ] Railway Deployment Guide
- [ ] Environment Configuration
- [ ] Business Context
- [ ] API Reference

### 📅 Planned
- [ ] Performance Optimization Guide
- [ ] Testing Strategy
- [ ] Internationalization Guide
- [ ] Monitoring & Observability

---

## 🤝 Contributing to Documentation

**Found a gap?** Open an issue or submit a PR.

**Documentation Standards:**
- Use clear, concise language
- Include code examples where helpful
- Link to related documentation
- Update "Last Updated" dates
- Keep this index current

**Documentation Location:**
- Project docs: `/docs/`
- Main README: `/README.md`
- Security: `/SECURITY.md`
- Contributing: `/CONTRIBUTING.md`

---

## 📞 Getting Help

- **Technical Questions:** Check relevant documentation above
- **Setup Issues:** See [Troubleshooting Guide](#) (coming soon)
- **Security Concerns:** See [Security Policy](../SECURITY.md)
- **General Questions:** Review [Main README](../README.md)

---

**Last Index Update:** 2025-01-29

