# AI_PLAYBOOK — CashPilot

## Purpose

Define **how AI tools (Copilot, Codex, ChatGPT, etc.) are used** in the CashPilot repository. This playbook exists to **augment human decision-making**, not replace it.

AI is treated as a **junior engineer**: fast, helpful, but never authoritative.

---

## Mandatory Reading Order for AI

Any AI-assisted task MUST follow this reading order:

1. `docs/README.md` (documentation authority and hierarchy)
2. `docs/product/PRODUCT_VISION.md`
3. `docs/product/REQUIREMENTS.md`
4. `docs/product/ACCEPTANCE_CRITERIA.md`
5. `docs/architecture/ARCHITECTURE.md`
6. `docs/architecture/CODE_MAP.md`
7. `docs/architecture/DATA_MODEL.md`
8. `docs/sdlc/DEFINITION_OF_READY.md`
9. `docs/sdlc/WORKFLOW.md`
10. `docs/sdlc/IMPLEMENTATION_PLAN.md`

If information is missing or ambiguous, AI must STOP and ask.

### Optional Reference Documentation

For specific tasks, consult these additional resources as needed:

* `docs/reference/API.md` — API endpoint reference (when adding/modifying endpoints)
* `docs/reference/GETTING_STARTED.md` — Development setup (for environment issues)
* `docs/reference/TROUBLESHOOTING.md` — Common problems and solutions (for debugging)
* `docs/reference/w7-compatibility.md` — Legacy browser support (for frontend changes)
* `docs/reference/features/*.md` — Feature-specific documentation (when working on existing features)
* `docs/runbooks/backup_restore.md` — Database operations (for migration work)

---

## Allowed Uses of AI

AI MAY be used to:

* Propose PR breakdowns after DoR is satisfied
* Generate code **only within documented architecture**
* Generate tests directly from Acceptance Criteria
* Refactor code when behavior is unchanged
* Suggest documentation improvements

---

## Forbidden Uses of AI

AI MUST NOT:

* Invent new features, roles, or workflows
* Change RBAC rules without documentation updates
* Introduce new architectural patterns
* Move business logic to the frontend
* Bypass validations or audit requirements
* Modify data model without updating DATA_MODEL.md
* Add dependencies without justification
* Remove or modify audit fields
* Change soft delete behavior
* Disable security checks or RBAC enforcement

---

## Required AI Output Contract

When asked to implement something, AI output MUST include:

1. **Understanding Summary**

   * Restate the problem and scope

2. **Impacted Areas**

   * Files and modules affected (per CODE_MAP)

3. **PR Plan**

   * Small PR breakdown

4. **Risk Assessment**

   * RBAC, data integrity, reporting risks

5. **Test Plan**

   * Tests to add or update

AI must not jump directly to code without this structure.

---

## Documentation Update Rules

When making code changes, AI MUST update corresponding documentation:

### Data Model Changes
* **Add/modify database table or column** → Update `docs/architecture/DATA_MODEL.md`
* **Create migration** → Document in migration file and update DATA_MODEL.md
* **Change entity relationships** → Update DATA_MODEL.md and relevant diagrams

### API Changes
* **Add new endpoint** → Update `docs/reference/API.md` with full specification
* **Modify endpoint behavior** → Update API.md and relevant feature docs
* **Change request/response format** → Update API.md with examples

### Feature Changes
* **Add new feature** → Create entry in `docs/implementation/IMPROVEMENT_BACKLOG.md` if not exists
* **Complete backlog item** → Update status with completion date
* **Significant feature work** → Consider adding to `docs/reference/features/`

### Architecture Changes
* **Change code organization** → Update `docs/architecture/CODE_MAP.md`
* **Add new architectural pattern** → Update `docs/architecture/ARCHITECTURE.md`
* **Change technology/dependencies** → Update README.md tech stack section

### RBAC Changes
* **Modify permissions** → Update `docs/product/ACCEPTANCE_CRITERIA.md` (AC-02)
* **Add new role behavior** → Update REQUIREMENTS.md and ACCEPTANCE_CRITERIA.md

**Rule:** If unsure which docs to update, STOP and ask.

---

## When to STOP and Ask

AI MUST pause and ask for clarification when encountering:

### Architectural Decisions
* **Caching strategy** — Where to cache? What TTL? How to invalidate?
* **New external service** — Which library? Authentication approach?
* **Performance optimization** — Trade-offs between approaches?
* **Async vs sync** — When to use which pattern?

### RBAC Ambiguity
* **Permission unclear** — Which role can perform action?
* **Cross-business access** — How should this work for admins vs cashiers?
* **New protected resource** — What's the access policy?

### Data Model Decisions
* **Relationship type** — Should this be 1:1, 1:N, or M:N?
* **Nullable fields** — Can this be null? What's the default?
* **Migration strategy** — How to handle existing data?
* **Cascade behavior** — What happens on delete?

### Business Logic Uncertainty
* **Calculation formula unclear** — What's the exact formula?
* **Edge case handling** — What happens when X occurs?
* **Validation rules** — What are the exact constraints?
* **Workflow ambiguity** — What's the exact user flow?

### Multiple Valid Approaches
* When 2+ implementation approaches exist with different trade-offs
* When the requirement can be interpreted in multiple ways
* When the change affects multiple systems/modules

**Default Action:** When in doubt, STOP and present options with pros/cons.

---

## Standard Prompt Template

Use this template when working with AI:

```
Read and comply with docs/sdlc/AI_PLAYBOOK.md.

Context:
- Goal:
- Relevant Acceptance Criteria:

Instructions:
1. Confirm Definition of Ready
2. Propose an Implementation Plan
3. Identify risks and tests
4. Only then provide code changes
```

---

## Standard Post-Commit Workflow

After implementing changes, AI MUST automatically:

1. **Create feature branch** with descriptive name
   ```bash
   git checkout -b <ticket-id>-brief-description
   ```

2. **Commit with structured message**
   - Format: `type(ticket): summary`
   - Include detailed bullet points of changes
   - Reference ticket number

3. **Push to remote**
   ```bash
   git push -u origin <branch-name>
   ```

4. **Generate PR description** using `.github/pull_request_template.md`
   - Auto-fill based on changes made
   - Include testing status
   - Check relevant boxes
   - Provide in a code block for easy copy-paste

**This workflow is mandatory for all feature work.** Do not wait for the user to ask.

### When Post-Commit Workflow Applies

**REQUIRED for:**
* New features or functionality
* Bug fixes that change behavior
* Refactors touching business logic, RBAC, or data model
* API endpoint additions or modifications
* Database migrations
* Template/UI changes that affect user workflow

**OPTIONAL for:**
* Documentation-only changes (no code)
* README updates
* Comment additions/clarifications
* Typo fixes in docs
* Formatting-only changes (running `make fmt`)

**When optional:** Ask user if they want standard git workflow or if they'll handle it manually.

---

## Adding to IMPROVEMENT_BACKLOG.md

When adding new items to the backlog, follow this structure:

### Placement
* Identify correct EPIC (or create new one if needed)
* Place within epic by severity: Critical > High > Medium > Low
* Assign ticket ID: `CP-<EPIC>-<NUMBER>`

### Required Fields
* **Severity:** Critical / High / Medium / Low
* **Problem:** Clear problem statement
* **Evidence:** File/line references or user story
* **Acceptance impact:** Which AC-* are affected
* **Status:** Not started / In progress / Completed (with date)

### Recommended Fields
* **User Story:** "As [role], I want [action], so that [benefit]"
* **Requirements:** Bullet list of what must be delivered
* **Technical Design:** High-level implementation approach
* **Implementation Steps:** Ordered list of work items
* **Dependencies:** What must exist first
* **Acceptance Criteria:** How to verify it works

### Priority Markers
* Add **HIGH PRIORITY / ASAP** for urgent items
* Add **Blocked by CP-XXX-YY** for dependencies
* Mark epic status when all items complete

### Example Format
```markdown
### CP-EPIC-01 — Short descriptive title

* **Severity:** High
* **Problem:** Clear statement of the problem
* **Evidence:** `file/path.py` line 123
* **User Story:** As admin, I want X, so that Y
* **Acceptance impact:** AC-06
* **Status:** Not started - **HIGH PRIORITY / ASAP**
* **Requirements:**
  - Requirement 1
  - Requirement 2
* **Technical Design:**
  - Design decision 1
  - Design decision 2
* **Dependencies:**
  - CP-OTHER-01 must be complete
```

---

## Review & Accountability

* All AI-generated code is reviewed as human-written code
* Responsibility remains with the human author
* If AI violates this playbook, the output is rejected
* Documentation updates are as important as code changes

---

## Change Control

Changes to this playbook require:

* Explicit discussion
* Update to this document