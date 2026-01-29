# CODE_MAP — CashPilot

## Purpose

Provide a **practical map of the codebase** so contributors and AI tools understand **where to add or change code** without guesswork. This document is **authoritative** for code placement.

---

## Top-Level Structure

```
.
├── src/
│   └── cashpilot/
│       ├── api/
│       ├── core/
│       ├── models/
│       ├── middleware/
│       ├── utils/
│       ├── scripts/
│       └── main.py
├── templates/
├── static/
├── tests/
├── alembic/
└── docs/
```

---

## Backend (`src/cashpilot`)

### `main.py`

* Application entrypoint
* App initialization and router inclusion
* Middleware registration

### `api/`

**What lives here:**

* Route definitions (HTTP endpoints)
* Request parsing and response shaping
* Dependency injection (auth, RBAC)

**What does NOT live here:**

* Business rules
* Database model definitions

---

### `core/`

**What lives here:**

* Authentication and session handling
* RBAC enforcement utilities
* Security helpers
* Configuration and settings

**Typical changes:**

* Adding new permission checks
* Modifying auth/session behavior

---

### `models/`

**What lives here:**

* SQLAlchemy models
* Pydantic schemas (if applicable)
* Data validation rules

**Rules:**

* No HTTP concerns
* No template logic

---

### `middleware/`

**What lives here:**

* Request/response middleware
* Logging and error handling
* Context injection (request ID, user)

---

### `utils/`

**What lives here:**

* Pure helper functions
* Formatting, parsing, shared logic

**Rules:**

* No database access
* No request context assumptions

---

### `scripts/`

**What lives here:**

* One-off maintenance or admin scripts
* Internal utilities not exposed as routes

---

## Frontend

### `templates/`

**What lives here:**

* Jinja2 templates
* Server-rendered views
* HTMX partials

**Rules:**

* No business logic
* Minimal control flow
* RBAC reflected only in visibility

---

### `static/`

**What lives here:**

* Compiled CSS
* Minimal JavaScript helpers

**Rules:**

* JS enhances UX only
* No calculations that affect correctness

---

## Tests (`tests/`)

**Structure:**

* Tests mirror backend structure
* Feature-focused test files

**Rules:**

* Tests assert behavior, not implementation
* RBAC and audit behavior must be covered

---

## Database & Migrations

### `alembic/`

* Database migration scripts
* Schema evolution history

**Rules:**

* Every schema change requires a migration
* No manual DB changes in production

---

## Documentation (`docs/`)

* `product/` → what the system must do
* `architecture/` → how the system is built
* `sdlc/` → how work is done
* `reference/` → historical context
* `runbooks/` → operational procedures

---

## Change Guidance

When adding a feature:

1. Update Product / Acceptance Criteria if scope changes
2. Identify affected modules via this map
3. Make the smallest possible changes
4. Add or update tests

If unsure where code belongs:

* Stop and update this document first