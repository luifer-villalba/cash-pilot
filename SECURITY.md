# Security Policy

This document tracks security vulnerabilities in CashPilot dependencies and documents any false positives or accepted risks.

## Security Audit Process

We use `pip-audit` to automatically scan for known vulnerabilities in Python dependencies. Audits run:
- **Automatically**: On every PR/push via GitHub Actions
- **Pre-commit**: Before each commit via pre-commit hooks
- **Monthly**: Manual full audit as backup

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on running security audits.

## How to Use This Document

### When CI/Pre-commit Fails Due to Vulnerabilities

1. **Run audit locally**: `make audit` to see the full details
2. **Check if already documented**: Look in "Resolved CVEs" or "False Positives" sections
3. **Take action**:
   - **Fix it**: Update the package version → Document in "Resolved CVEs"
   - **Can't fix**: Document in "False Positives / Accepted Risks" with justification
4. **Commit the fix + SECURITY.md update** together

### Monthly Audit Workflow

1. Run `make audit-full` on the first Monday of each month
2. Review all findings (not just critical)
3. For each vulnerability:
   - Update package if fix available → Add to "Resolved CVEs"
   - If not fixable/acceptable → Add to "False Positives" with justification
   - Update "Last Audit" date
4. Commit changes to SECURITY.md

### Example Scenarios

**Scenario 1: CVE found, fix available**
- Update `pyproject.toml` with secure version
- Add entry to "Resolved CVEs" section
- Run tests to verify compatibility
- Commit both changes

**Scenario 2: CVE found, but false positive**
- Example: CVE affects a feature we don't use
- Add entry to "False Positives" with explanation
- Include mitigation measures if any
- Commit SECURITY.md update

**Scenario 3: CVE found, fix breaks our code**
- Document in "False Positives" with:
  - Why we can't upgrade (breaking changes)
  - Workarounds/mitigations in place
  - Timeline for future resolution

## Vulnerability Severity Levels

- **Critical**: Must be resolved before merging
- **High**: Should be resolved promptly
- **Medium/Low**: Tracked and addressed based on risk assessment

## Documented Vulnerabilities

### Active CVEs

*No active critical or high-severity CVEs at this time.*

### Resolved CVEs

#### CVE-2024-47874 (Starlette)

**Severity**: High  
**Status**: Resolved  
**Link**: [CVE-2024-47874](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2024-47874)

**Description**: DoS vulnerability in Starlette's multipart/form-data parsing. Form fields without filenames are buffered in memory with no size limit, allowing attackers to cause excessive memory consumption and server slowdown/OOM.

**Resolution**: Updated Starlette from `>=0.37.0` to `>=0.49.1` (fixed in 0.40.0, fully resolved in 0.49.1)  
**Date Resolved**: 2025-01-29

#### CVE-2025-54121 (Starlette)

**Severity**: Low  
**Status**: Resolved  
**Link**: [CVE-2025-54121](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2025-54121)

**Description**: When parsing multi-part forms with large files, Starlette blocks the main thread to roll files over to disk, blocking the event loop and preventing new connections.

**Resolution**: Updated Starlette to `>=0.49.1` (fixed in 0.47.2, fully resolved in 0.49.1)  
**Date Resolved**: 2025-01-29

#### CVE-2025-62727 (Starlette)

**Severity**: High  
**Status**: Resolved  
**Link**: [CVE-2025-62727](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2025-62727)

**Description**: DoS vulnerability in Starlette's `FileResponse` Range header parsing. An unauthenticated attacker can send a crafted HTTP Range header that triggers quadratic-time processing, causing CPU exhaustion and denial-of-service for endpoints serving files (e.g., `StaticFiles` or `FileResponse`).

**Resolution**: Updated FastAPI to `>=0.128.0` and Starlette to `>=0.49.1` (fixed in Starlette 0.49.1)  
**Date Resolved**: 2025-01-29

## False Positives / Accepted Risks

This section documents vulnerabilities that are false positives or accepted risks with justification.

### Template Entry Format

```markdown
### CVE-YYYY-XXXXX (Package Name)

**Severity**: Critical/High/Medium/Low  
**Status**: False Positive / Accepted Risk  
**Link**: [CVE Details](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-YYYY-XXXXX)

**Justification**: 
- Explanation of why this is a false positive or why the risk is acceptable
- Any mitigation measures in place
- Impact assessment

**Last Reviewed**: YYYY-MM-DD
```


## Reporting Security Issues

If you discover a security vulnerability in CashPilot itself (not a dependency), please:

1. **Do not** open a public issue
2. Email the maintainers directly with details
3. Include steps to reproduce (if applicable)
4. Allow time for assessment and patching before public disclosure

## Dependency Updates

We regularly update dependencies to address security vulnerabilities. All updates are:
- Tested thoroughly before deployment
- Documented in commit messages and PR descriptions
- Reviewed for breaking changes

## Monthly Audit Schedule

Manual security audits are performed on the **first Monday of each month** (or as needed). Results are reviewed and any new vulnerabilities are addressed or documented here.

**Last Audit**: 2025-01-29 (Initial audit completed, 3 CVEs resolved in Starlette: CVE-2024-47874, CVE-2025-54121, CVE-2025-62727)
