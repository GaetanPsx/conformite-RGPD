<!--
Sync Impact Report
Version change: [TEMPLATE] → 1.0.0 (initial ratification)
Modified principles: n/a (first concrete version; all 5 slots filled from template placeholders)
Added sections:
  - Core Principles: I. Legal Fidelity & Traceability, II. Test-First Verification,
    III. Auditability & Explainability, IV. Privacy-by-Design (Self-Application),
    V. Simplicity & Maintainability
  - Data Handling & Security Requirements (Section 2)
  - Development Workflow & Quality Gates (Section 3)
  - Governance
Removed sections: none (template placeholders only)
Templates requiring follow-up: none — dependent templates (plan/spec/tasks) read this file at
  runtime and are not modified by this command.
Deferred TODOs: none
-->

# conformite-RGPD Constitution

## Core Principles

### I. Legal Fidelity & Traceability
Every compliance check, rule, or finding the tool produces MUST be traceable to a specific
GDPR article, recital, or recognized regulatory guidance (e.g., CNIL, EDPB). No check may assert
a compliance or non-compliance verdict without citing its legal basis. When a rule encodes an
interpretation of ambiguous regulatory text, that interpretation MUST be documented alongside
the rule, not only in commit history.
**Rationale**: This is a legal-compliance tool; an inaccurate or uncited finding is worse than
no finding, since users may act on it directly. Traceability is what makes the tool's output
defensible and auditable.

### II. Test-First Verification (NON-NEGOTIABLE)
Every compliance rule or check MUST have automated tests covering at least one compliant and
one non-compliant case before the rule is considered done. Tests MUST be written and reviewed
before (or alongside) the implementation; a rule without a failing-then-passing test is not
merged. Regressions in existing rules MUST block release.
**Rationale**: False negatives (missed violations) and false positives (incorrect flags) both
carry real consequences for users relying on this tool to assess legal risk. Test-first
discipline is the primary defense against silently wrong compliance logic.

### III. Auditability & Explainability
All tool output MUST be reproducible (same input + same rule version → same result) and MUST
explain *why* a verdict was reached in terms a non-engineer can follow — not just a pass/fail
flag. Rule versions and their effective dates MUST be tracked so past assessments remain
explainable even after rules change.
**Rationale**: Compliance findings are often reviewed by non-technical stakeholders (legal,
DPOs, auditors) who need to understand and trust the reasoning, not just the score.

### IV. Privacy-by-Design (Self-Application)
The tool itself MUST follow the GDPR principles it checks for: data minimization (collect only
what is needed to run an assessment), storage limitation (no indefinite retention of scanned
data without justification), and security of any personal data it processes or stores at rest
and in transit. Any personal data ingested for analysis MUST be clearly scoped and documented.
**Rationale**: A GDPR compliance tool that itself mishandles personal data undermines its own
credibility and could create the very risk it is meant to detect.

### V. Simplicity & Maintainability
Start with the simplest design that satisfies the current requirement; avoid speculative
abstractions, unused configuration flags, or premature generalization of rules. New complexity
(new rule engines, new dependencies, new abstractions) MUST be justified by a concrete,
current need, not a hypothetical future one.
**Rationale**: As a student project with a small maintainer base, complexity that isn't earned
becomes debt no one has time to pay down, and obscures the legal logic the tool exists to make
clear.

## Data Handling & Security Requirements

Any personal data (real or synthetic) used in development, testing, or demos MUST be clearly
labeled as such and MUST NOT include real personal data belonging to identifiable individuals
unless explicit, documented consent exists. Secrets, API keys, and credentials MUST NOT be
committed to the repository. Dependencies that process or transmit user data to third parties
MUST be disclosed in project documentation before being introduced.

## Development Workflow & Quality Gates

All changes affecting compliance rules or their output MUST go through review before merge,
with the reviewer explicitly checking the change against Principle I (Legal Fidelity) and
Principle II (Test-First Verification). Pull requests that add or modify a rule MUST link to
the regulatory text or guidance the rule is based on. CI MUST run the full rule test suite
before merge is permitted.

## Governance

This constitution supersedes other informal practices for this project. Amendments require:
(1) a documented rationale for the change, (2) an update to this file following the versioning
policy below, and (3) review by the project maintainer(s) before the amendment takes effect.

Versioning policy (semantic versioning applied to governance):
- MAJOR: Backward-incompatible removal or redefinition of a principle or governance rule.
- MINOR: A new principle or materially expanded section is added.
- PATCH: Wording clarifications, typo fixes, or non-semantic refinements.

All pull requests and reviews MUST verify compliance with this constitution. Any deviation must
be explicitly justified in the PR description; unjustified complexity or skipped tests are
grounds for rejection. Use repository CLAUDE.md files (if present) for day-to-day runtime
development guidance that supplements, but does not override, this constitution.

**Version**: 1.0.0 | **Ratified**: 2026-09-16 | **Last Amended**: 2026-09-16
