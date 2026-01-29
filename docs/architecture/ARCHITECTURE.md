# ARCHITECTURE — CashPilot

## Purpose

Document the **current, intentional architecture** of CashPilot. This file defines **how the system is structured and why**, based on existing implementation. It is **authoritative**: new code must conform to it unless an explicit architecture change is approved.

This document describes **what exists**, not aspirational redesigns.

---

## Architectural Principles

* **Server-rendered first**: Reliability over client complexity
* **Minimal JavaScript**: Enhance UX, never own business logic
* **Backend-enforced RBAC**: UI restrictions are not sufficient
* **Auditability by default**: All critical actions are traceable
* **Legacy compatibility**: Windows 7 and older browsers are supported

---

## High-Level System Overview

### Backend

* **Framework**: FastAPI
* **Execution model**: ASGI (async)
* **ORM**: SQLAlchemy (async)
* **Migrations**: Alembic
* **Database**: PostgreSQL

Responsibilities:

* Authentication & session management
* RBAC enforcement
* Business logic and validations
* Report aggregation
* Audit trail persistence

---

### Frontend

* **Templates**: Jinja2
* **Styling**: Tailwind CSS + DaisyUI
* **Interactivity**: HTMX + small vanilla JS helpers

Characteristics:

* No SPA framework
* Pages render fully server-side
* HTMX used for partial updates and actions
* JavaScript never contains business rules

---

## Application Structure

```
src/cashpilot/
  api/          # Routes and request handling
  core/         # Auth, RBAC, configuration, security
  models/       # Database models and schemas
  middleware/   # Logging, error handling, request context
  utils/        # Shared helpers
  scripts/      # Maintenance and internal tasks
```

* `templates/` contains all HTML views
* `static/` contains CSS and minimal JS

---

## Authentication & Authorization

* Session-based authentication
* Sessions stored server-side
* RBAC enforced in backend dependencies
* All routes validate user role and business assignment

UI elements reflect permissions but **do not enforce them**.

---

## Data Integrity & Auditability

* **Soft deletes** for critical entities
* Audit fields include:

  * created_at / updated_at
  * created_by / updated_by
* Historical records are never silently removed

Timezone handling:

* All timestamps are timezone-aware
* Paraguay context is the default

---

## Reporting Architecture

* Reports are computed server-side
* Data aggregation uses persisted records only
* No client-side calculations for totals
* PDF export uses server-rendered HTML → PDF

---

## Non-Functional Constraints

### Compatibility

* Must function on Windows 7
* Avoid modern JS APIs unsupported by legacy browsers

### Performance

* Optimized for low-end hardware
* Predictable response times preferred over async fan-out

### Security

* No cross-business data access
* All critical paths validated server-side

---

## Explicit Non-Goals

* No SPA rewrite
* No offline mode
* No client-side state ownership
* No microservices decomposition

---

## Change Control

Any architectural change must:

* Be documented via ADR
* Update this file
* Be reviewed separately from feature work