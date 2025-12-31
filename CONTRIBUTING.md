# Contributing to CashPilot

Thank you for your interest in contributing to CashPilot! This document provides guidelines and instructions for contributing.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/luifer-villalba/cash-pilot.git
   cd cash-pilot
   ```

2. Set up your environment:
   ```bash
   # Create .env file (see docker-compose.yml for required variables)
   make build
   make up
   make migrate
   ```

3. Install pre-commit hooks:
   ```bash
   # Install pre-commit (if not already installed)
   pip install pre-commit
   
   # Install pip-audit locally for pre-commit hook (or use Docker)
   pip install pip-audit
   
   # Install pre-commit hooks
   pre-commit install
   ```

   **Note**: The `pip-audit` pre-commit hook requires `pip-audit` to be installed in your local Python environment. If you prefer to use Docker exclusively, you can skip the pre-commit hook and rely on CI for security audits.

## Code Quality

Before submitting a pull request, ensure:

- **Tests pass**: `make test`
- **Code is formatted**: `make fmt`
- **Linting passes**: `make lint`
- **Security audit passes**: See [Security Audits](#security-audits) below

## Security Audits

We use `pip-audit` to ensure our Python dependencies are secure and free from known vulnerabilities.

### Running Security Audits Locally

Run the security audit before submitting a pull request:

```bash
# Using Makefile (recommended)
make audit

# Or directly with Docker
docker compose run --rm --no-deps app bash -lc "pip-audit --desc"

# Or if running locally with pip-audit installed
pip-audit --desc
```

The audit will:
- Check all installed Python packages for known CVEs
- Display descriptions of any vulnerabilities found
- **Fail if any vulnerabilities are detected** (pip-audit exits with non-zero code on any findings)

**Note**: You may see a warning about the local `cashpilot` package not being found on PyPI. This is expected and can be ignored - `pip-audit` only audits packages available on PyPI, not local development packages.

### Pre-commit Hook

The pre-commit hook automatically runs `pip-audit` before each commit. If any vulnerabilities are detected, the commit will be blocked.

To run the hook manually:
```bash
pre-commit run pip-audit --all-files
```

### CI/CD Integration

Security audits run automatically in GitHub Actions on:
- Every pull request
- Every push to `main` or `dev` branches

The CI job will fail if any vulnerabilities are detected, preventing merge of insecure code.

### Monthly Manual Audit

As a backup to automated checks, perform a monthly manual audit:

```bash
# Run full audit with all severity levels (using Makefile)
make audit-full

# Or directly with Docker
docker compose run --rm --no-deps app bash -lc "pip-audit --desc"

# Review output and address any new vulnerabilities
# Document false positives in SECURITY.md if needed
```

**Schedule**: First Monday of each month (or as needed)

### Handling Vulnerabilities

1. **Critical/High CVEs**: Must be resolved before merging
   - Update the affected package to a secure version
   - Test thoroughly after updating
   - If update is not possible, document in `SECURITY.md` with justification

2. **Medium/Low CVEs**: Should be addressed in a timely manner
   - Create a ticket for tracking
   - Prioritize based on exploitability and impact

3. **False Positives / Accepted Risks**: Document in `SECURITY.md`
   - Include CVE ID and link
   - Explain why it's a false positive or why the risk is acceptable
   - Note any mitigation measures in place
   - If truly unfixable, add `--ignore-vuln CVE-XXXX-XXXXX` to `pip-audit` commands in Makefile, CI, and pre-commit config

See [SECURITY.md](SECURITY.md) for documented vulnerabilities and false positives.

## Commit Messages

Use Linear ticket references (MIZ-XXX prefix) in commit messages:

```bash
git commit -m "feat: add new feature (MIZ-123)"
git commit -m "fix: resolve security vulnerability (MIZ-456)"
```

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Ensure all checks pass (tests, linting, security audit)
4. Push to your fork: `git push origin feature/your-feature`
5. Create a pull request to `main` or `dev`
6. Reference the Linear ticket in the PR description

## Questions?

If you have questions or need help, please open an issue or contact the maintainers.
