> 📚 Reference Document  
> This document provides historical context or detailed guidance.  
> It does NOT define product requirements or architecture authority.

# Architecture Decision Records (ADRs)

This document records the key architectural decisions made for CashPilot, explaining the "why" behind technical choices.

**Last Updated:** 2025-01-29

---

## ADR-001: FastAPI over Django/Flask

**Status:** Accepted  
**Date:** 2024-12-01  
**Context:** Need for modern async Python web framework with excellent performance and type safety.

**Decision:** Use FastAPI as the primary web framework.

**Rationale:**
- **Async-first:** Native async/await support for database operations (critical for multi-location concurrent sessions)
- **Type Safety:** Built-in Pydantic validation and type hints reduce runtime errors
- **Performance:** One of the fastest Python frameworks (comparable to Node.js/Go)
- **Modern Python:** Leverages Python 3.12+ features (type hints, dataclasses)
- **API Documentation:** Automatic OpenAPI/Swagger docs (useful for future API expansion)
- **Developer Experience:** Excellent IDE support with type hints

**Alternatives Considered:**
- **Django:** Too heavy, synchronous by default, ORM not as flexible
- **Flask:** No built-in async support, requires more boilerplate
- **Tornado:** Less modern, smaller ecosystem

**Consequences:**
- ✅ Excellent async database performance
- ✅ Type safety catches errors at development time
- ⚠️ Smaller ecosystem than Django (fewer third-party packages)
- ⚠️ Requires Python 3.12+ (acceptable trade-off)

---

## ADR-002: Server-Rendered Templates over SPA

**Status:** Accepted  
**Date:** 2024-12-01  
**Context:** Need for fast page loads, SEO (if needed), and simplicity for non-technical users.

**Decision:** Use server-rendered Jinja2 templates instead of a Single Page Application (SPA).

**Rationale:**
- **Simplicity:** Business staff aren't tech-savvy; server-rendered pages are more predictable
- **Performance:** Initial page load is faster (no JavaScript bundle download)
- **SEO:** If we need public pages later, server-rendered is better
- **HTMX:** Provides SPA-like interactivity without framework complexity
- **Maintenance:** Less JavaScript to maintain, fewer dependencies
- **Windows 7 Support:** Easier to ensure compatibility with server-rendered HTML

**Alternatives Considered:**
- **React/Vue SPA:** More complex, larger bundle size, harder Windows 7 support
- **Next.js:** Overkill for this use case, adds Node.js dependency

**Consequences:**
- ✅ Faster initial page loads
- ✅ Simpler mental model for developers
- ✅ Better Windows 7 compatibility
- ⚠️ Less dynamic interactivity (mitigated by HTMX)
- ⚠️ More server-side rendering load (acceptable for this scale)

---

## ADR-003: Session-Based Auth over JWT

**Status:** Accepted  
**Date:** 2024-12-01  
**Context:** Need for simple, secure authentication that works across browser reloads.

**Decision:** Use server-side session-based authentication (Starlette SessionMiddleware) instead of JWT tokens.

**Rationale:**
- **User Experience:** Users stay logged in across browser reloads (no token expiration issues)
- **Simplicity:** No token refresh logic, no client-side token storage
- **Security:** Server-side sessions can be invalidated immediately (important for business apps)
- **Business Context:** Cashiers work on shared terminals; session timeout (10hrs cashier, 2hrs admin) is appropriate
- **HTMX Compatibility:** Sessions work seamlessly with HTMX requests

**Alternatives Considered:**
- **JWT:** More complex, requires refresh token logic, harder to invalidate
- **OAuth:** Overkill for internal business app

**Consequences:**
- ✅ Simple implementation
- ✅ Easy logout (just clear session)
- ✅ Works well with HTMX
- ⚠️ Requires server-side session storage (acceptable with Railway)
- ⚠️ Not stateless (acceptable trade-off)

---

## ADR-004: PostgreSQL + Async SQLAlchemy

**Status:** Accepted  
**Date:** 2024-12-01  
**Context:** Need for reliable relational database with excellent async support.

**Decision:** Use PostgreSQL with SQLAlchemy 2.0 async (asyncpg driver).

**Rationale:**
- **Reliability:** PostgreSQL is battle-tested for production workloads
- **Async Support:** SQLAlchemy 2.0 has excellent async support (critical for FastAPI)
- **Multi-Location:** Concurrent sessions require proper connection pooling (async handles this well)
- **Data Integrity:** Foreign keys, constraints, transactions ensure data consistency
- **Migrations:** Alembic provides versioned schema migrations
- **Timezone Support:** PostgreSQL has excellent timezone handling (critical for Paraguay timezone)

**Alternatives Considered:**
- **SQLite:** Not suitable for production, no async support
- **MySQL:** Less mature async support, timezone handling issues
- **MongoDB:** No relational integrity, overkill for structured data

**Consequences:**
- ✅ Excellent async performance
- ✅ Data integrity guarantees
- ✅ Production-ready
- ⚠️ Requires managed database (Railway PostgreSQL)
- ⚠️ More complex than SQLite (acceptable trade-off)

---

## ADR-005: Soft Deletes over Hard Deletes

**Status:** Accepted  
**Date:** 2024-12-01  
**Context:** Accounting requirements need full audit trail; nothing should be permanently lost.

**Decision:** Implement soft deletes (is_deleted flag) for businesses and cash sessions instead of hard deletes.

**Rationale:**
- **Audit Requirements:** Accountants need to see full history, even for "deleted" records
- **Recovery:** Accidental deletions can be recovered (important for business data)
- **Statistics:** Deleted sessions excluded from statistics but preserved for audit
- **Compliance:** Financial records must be retained (soft delete preserves data)
- **User Experience:** Admins can restore deleted sessions if needed

**Implementation:**
- `CashSession.is_deleted` flag with `deleted_at` and `deleted_by` timestamps
- `Business.is_active` flag (inverse: active = not deleted)
- Deleted sessions filtered out of normal queries but accessible to admins
- Statistics queries explicitly exclude deleted sessions

**Alternatives Considered:**
- **Hard Deletes:** Loses audit trail, can't recover mistakes
- **Archive Table:** More complex, requires data migration

**Consequences:**
- ✅ Full audit trail preserved
- ✅ Recovery possible
- ✅ Statistics remain accurate (exclude deleted)
- ⚠️ More complex queries (need to filter is_deleted)
- ⚠️ Database grows (acceptable trade-off)

---

## ADR-006: Structured Logging with Request IDs

**Status:** Accepted  
**Date:** 2024-12-01  
**Context:** Need to trace requests through logs for debugging production issues.

**Decision:** Use structured JSON logging with request correlation IDs.

**Rationale:**
- **Debugging:** Request IDs allow tracing a single request through all log entries
- **Production:** Railway logs are easier to search with structured JSON
- **Observability:** Can correlate logs with Sentry errors using request ID
- **Tooling:** JSON logs work well with log aggregation tools (if needed later)

**Implementation:**
- `structlog` for structured logging
- `RequestIDMiddleware` generates UUID per request
- All log entries include `request_id` field
- Sentry integration includes request ID in error context

**Alternatives Considered:**
- **Plain Text Logs:** Harder to parse, no correlation
- **Log Levels Only:** Not enough context for debugging

**Consequences:**
- ✅ Easy request tracing
- ✅ Better production debugging
- ✅ Integrates with Sentry
- ⚠️ Slightly more verbose logs (acceptable trade-off)

---

## ADR-007: Cache Versioning Strategy

**Status:** Accepted  
**Date:** 2024-12-15  
**Context:** Report calculations are expensive; need caching but must handle logic changes.

**Decision:** Use versioned cache keys (e.g., `weekly_trend_v4`) that increment when calculation logic changes.

**Rationale:**
- **Performance:** Reports require expensive calculations (aggregations, date math)
- **Logic Changes:** When calculation logic changes, old cache entries become invalid
- **No Manual Flush:** Version increment naturally expires old entries via TTL
- **Simplicity:** No need for cache invalidation logic

**Implementation:**
- Cache keys include version constant: `CACHE_VERSION = 4`
- When logic changes, increment version: `CACHE_VERSION = 5`
- Old entries expire naturally (5min for current week, 1hr for historical)
- No manual cache clearing needed

**Alternatives Considered:**
- **Manual Cache Invalidation:** More complex, error-prone
- **No Versioning:** Stale data after logic changes
- **Timestamp-Based:** More complex, requires tracking last change time

**Consequences:**
- ✅ Simple to maintain
- ✅ No stale data issues
- ✅ Automatic expiration
- ⚠️ Must remember to increment version (documented in code comments)

---

## ADR-008: Windows 7 Compatibility

**Status:** Accepted  
**Date:** 2024-12-20  
**Context:** Many businesses in target market still use Windows 7 machines.

**Decision:** Maintain compatibility with Windows 7 browsers (IE11, Chrome 50+, Firefox 45+).

**Rationale:**
- **Market Reality:** Small businesses use legacy hardware due to budget constraints
- **Accessibility:** Supporting W7 ensures all potential users can access the system
- **Business Impact:** Not supporting W7 would exclude significant portion of target market

**Implementation:**
- JavaScript polyfills for missing features (Promise, fetch, Array methods)
- CSS fallbacks for unsupported features (CSS variables, backdrop-filter)
- PostCSS/Autoprefixer configured for IE11+ support
- Feature detection and graceful degradation

**Alternatives Considered:**
- **Modern Browsers Only:** Would exclude W7 users (unacceptable)
- **Separate Legacy Version:** Too complex to maintain

**Consequences:**
- ✅ Accessible to all users
- ✅ Larger market reach
- ⚠️ More complex frontend code (polyfills, fallbacks)
- ⚠️ Testing overhead (must test on W7)

**See Also:** [Windows 7 Compatibility Guide](w7-compatibility.md)

---

## ADR-009: Tailwind CSS + DaisyUI

**Status:** Accepted  
**Date:** 2024-12-01  
**Context:** Need for consistent, accessible UI with minimal custom CSS.

**Decision:** Use Tailwind CSS 4.x with DaisyUI plugin for component styling.

**Rationale:**
- **Consistency:** DaisyUI provides pre-built accessible components
- **Speed:** Rapid UI development without writing custom CSS
- **Maintainability:** Utility-first approach reduces CSS bloat
- **Accessibility:** DaisyUI components include ARIA attributes
- **Theme Support:** Built-in light/dark theme support (if needed later)

**Alternatives Considered:**
- **Bootstrap:** More opinionated, larger bundle
- **Custom CSS:** Too much maintenance overhead
- **Material UI:** React-focused, not suitable for server-rendered templates

**Consequences:**
- ✅ Fast development
- ✅ Consistent design system
- ✅ Good accessibility defaults
- ⚠️ Learning curve for Tailwind utility classes
- ⚠️ Bundle size (mitigated by PostCSS purging)

---

## ADR-010: HTMX for Interactivity

**Status:** Accepted  
**Date:** 2024-12-01  
**Context:** Need for dynamic interactions without full SPA framework.

**Decision:** Use HTMX for dynamic page updates (pagination, form submissions, inline edits).

**Rationale:**
- **Simplicity:** Declarative attributes (hx-get, hx-post) instead of JavaScript
- **Server-Rendered:** Works seamlessly with Jinja2 templates
- **Progressive Enhancement:** Falls back to regular forms if JavaScript disabled
- **Small Bundle:** HTMX is lightweight (~10KB)
- **Windows 7 Compatible:** Works with polyfills

**Alternatives Considered:**
- **jQuery:** More verbose, larger bundle
- **Vanilla JavaScript:** Too much boilerplate
- **Alpine.js:** More complex, larger bundle

**Consequences:**
- ✅ Simple, declarative syntax
- ✅ Works with server-rendered templates
- ✅ Small bundle size
- ⚠️ Less flexible than full JavaScript framework (acceptable trade-off)

---

## Future Decisions (To Be Documented)

- **ADR-011:** Why Python 3.12+ (type system features, performance)
- **ADR-012:** Why Railway over other hosting (simplicity, PostgreSQL included)
- **ADR-013:** Why Alembic over raw SQL migrations (version control, rollback)
- **ADR-014:** Why Pydantic v2 for validation (performance, type safety)

---

## ADR Template

When documenting new decisions, use this template:

```markdown
## ADR-XXX: [Decision Title]

**Status:** [Proposed | Accepted | Rejected | Deprecated]  
**Date:** YYYY-MM-DD  
**Context:** [What situation led to this decision?]

**Decision:** [What was decided?]

**Rationale:**
- [Reason 1]
- [Reason 2]

**Alternatives Considered:**
- [Alternative 1]: [Why rejected]
- [Alternative 2]: [Why rejected]

**Consequences:**
- ✅ [Positive consequence]
- ⚠️ [Trade-off or negative consequence]
```

---

**Last Updated:** 2025-01-29  
**Maintained By:** Development Team
