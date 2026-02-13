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

---

## Review & Accountability

* All AI-generated code is reviewed as human-written code
* Responsibility remains with the human author
* If AI violates this playbook, the output is rejected

---

## Change Control

Changes to this playbook require:

* Explicit discussion
* Update to this document