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
   make seed   # Optional: load demo data
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

**📖 Detailed Setup Guide:** See [Getting Started Guide](docs/reference/GETTING_STARTED.md) for comprehensive setup instructions.

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

---

## Running Tests

Run the full test suite:

```bash
make test
```

Run specific test file:

```bash
docker compose exec app pytest tests/test_auth.py
```

Run specific test:

```bash
docker compose exec app pytest tests/test_auth.py::test_login_success -v
```

Run with coverage:

```bash
docker compose exec app pytest --cov=cashpilot tests/
```

---

## Working with Migrations

### Create a New Migration

```bash
# Auto-generate migration from model changes
make migration-create message="add new field to user"

# Or manually
docker compose exec app alembic revision --autogenerate -m "your message"
```

### Apply Migrations

```bash
# Apply all pending migrations
make migrate

# Or manually
docker compose exec app alembic upgrade head
```

### Rollback Migration

```bash
# Rollback one migration
docker compose exec app alembic downgrade -1

# Rollback to specific revision
docker compose exec app alembic downgrade <revision_id>
```

### View Migration History

```bash
docker compose exec app alembic history
docker compose exec app alembic current
```

---

## Working with Translations

CashPilot supports internationalization (i18n) using Babel.

### Extract Translatable Strings

After adding new `{{ _('Text') }}` in templates or `_('Text')` in Python code:

```bash
# Extract all translatable strings
docker compose exec app pybabel extract -F babel.cfg -o translations/messages.pot .
```

### Update Translation Files

```bash
# Update Spanish (Paraguay) translations
docker compose exec app pybabel update -i translations/messages.pot -d translations -l es_PY
```

### Edit Translations

Edit the `.po` file:
```bash
vim translations/es_PY/LC_MESSAGES/messages.po
```

Find entries like:
```po
#: templates/index.html:42
msgid "Dashboard"
msgstr "Panel de Control"  # Add your translation here
```

### Compile Translations

After editing `.po` files:

```bash
docker compose exec app pybabel compile -d translations
```

### Testing Translations

1. Change your browser language to Spanish
2. Reload the page
3. Verify translations appear correctly

---

## Code Quality Tools

### Format Code

```bash
# Auto-format with black and isort
make fmt
```

### Lint Code

```bash
# Run ruff linter
make lint
```

### Type Checking

```bash
# Run mypy (if configured)
docker compose exec app mypy src/
```

---

## Debugging Tips

### View Application Logs

```bash
# Live logs
make logs

# Or manually
docker compose logs -f app
```

### Access Python Shell

```bash
docker compose exec app python
```

Then explore:
```python
from cashpilot.models import User, Business, CashSession
# Play with models
```

### Database Shell

```bash
docker compose exec db psql -U cashpilot_user -d cashpilot
```

---

## Pull Request Guidelines

### Before Submitting

- [ ] Tests pass (`make test`)
- [ ] Code formatted (`make fmt`)
- [ ] Linting passes (`make lint`)
- [ ] Security audit passes (`make audit`)
- [ ] Documentation updated (if applicable)
- [ ] Translations added (if new UI strings)

### PR Description Template

Use `.github/pull_request_template.md`:

- Clear description of changes
- Link to related issue/ticket
- Test coverage explanation
- Screenshots (if UI changes)
- Breaking changes noted (if any)

### PR Size

- Keep PRs small and focused (< 400 lines changed preferred)
- One feature or fix per PR
- Break large changes into multiple PRs

### Review Process

1. Automated checks must pass (CI/CD)
2. Code review by maintainer
3. Address feedback
4. Squash commits if needed
5. Merge when approved

---

## Documentation Guidelines

All documentation changes should:

- Follow existing structure (see `docs/README.md`)
- Use clear, concise language
- Include code examples where helpful
- Update cross-references if needed

**Documentation Types:**
- **Product** (`docs/product/`) - What and why
- **Architecture** (`docs/architecture/`) - How it's built
- **SDLC** (`docs/sdlc/`) - How we work
- **Reference** (`docs/reference/`) - Guides and references
- **Runbooks** (`docs/runbooks/`) - Operational procedures

See [Documentation Index](docs/README.md) for full documentation map.

---

## Common Development Tasks

### Reset Database (Development Only)

**⚠️ CAUTION: This deletes all data**

```bash
docker compose down
docker volume rm cash-pilot_postgres_data
docker compose up -d
make migrate
make seed  # Reload demo data
```

### Update Dependencies

```bash
# Update pyproject.toml
vim pyproject.toml

# Rebuild container
docker compose build app

# Verify
docker compose exec app pip list
```

### Add New Endpoint

1. Add route in `src/cashpilot/api/routes/` or `src/cashpilot/api/*.py`
2. Add RBAC dependency (`require_admin` or `require_cashier`)
3. Add tests in `tests/`
4. Update API documentation in `docs/reference/API.md`
5. Test manually and via automated tests

### Add New Model Field

1. Update model in `src/cashpilot/models/`
2. Create migration: `make migration-create message="add field"`
3. Apply migration: `make migrate`
4. Update `docs/architecture/DATA_MODEL.md`
5. Add tests
6. Update relevant API endpoints and forms

---

## Getting Help

**Before Asking:**
1. Check [Getting Started Guide](docs/reference/GETTING_STARTED.md)
2. Search [Troubleshooting Guide](docs/reference/TROUBLESHOOTING.md)
3. Read relevant documentation in `docs/`
4. Search existing GitHub issues

**Where to Ask:**
- **GitHub Issues:** Bug reports, feature requests
- **GitHub Discussions:** Questions, ideas
- **Email:** Contact maintainers directly

---

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
