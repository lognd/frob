---
id: T-0452
title: 'invariant density lint: advisory when a spec section describes behavior but
  anchors ZERO invariants (section-level under-specification signal, complements the
  per-claim must/must-not lint)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/invariants.py
- src/frob/gates/
- docs/
- tests/test_gates.py
- pyproject.toml
- CHANGELOG.md
- uv.lock
- .frob-release.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-0452 gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
- op: add
  glob: pyproject.toml
  reason: REL001 bump required by adding public API (inv004_gate, find_normative_claims,
    NORMATIVE_CLAIM_PATTERNS)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 bump required by adding public API (inv004_gate, find_normative_claims,
    NORMATIVE_CLAIM_PATTERNS)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: REL001 bump required by adding public API (inv004_gate, find_normative_claims,
    NORMATIVE_CLAIM_PATTERNS)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 bump required by adding public API (inv004_gate, find_normative_claims,
    NORMATIVE_CLAIM_PATTERNS)
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestInv004Gate::test_section_with_normative_language_and_no_invariant_is_advisory
- tests/test_gates.py::TestInv004Gate::test_section_with_any_invariant_marker_is_silent
- tests/test_gates.py::TestInv004Gate::test_section_with_no_normative_language_is_silent
- tests/test_gates.py::TestInv004Gate::test_two_sections_only_flags_the_underspecified_one
- tests/test_gates.py::TestInv004Gate::test_missing_docs_dir_is_silent
designated_repro_test: null
threat: null
component: null
---
User request 2026-07-20: frob already lints per-CLAIM ("must"/"must not"/
"never"/"always"/"shall" language must have a bound invariant). Add the
INVERSE, section-level signal: if a documentation section/paragraph
describes behavior but anchors ZERO invariants, raise an ADVISORY -- a
behavior-describing section with no formal invariant at all is a likely
under-specified region, the "silence" the per-claim lint cannot see (no
explicit must/must-not token to trigger on).

Design (advisory, waivable, complements not replaces the per-claim lint):
- Section granularity: markdown headings (## / ###) define sections; also
  the module-doc / design-doc bodies frob already tracks. Per section,
  compare bound-invariant count (frob:invariant edges / INV- refs anchored
  in that section) against a "describes behavior" heuristic.
- "Describes behavior" heuristic (HARDEN into a closed, tunable signal, do
  NOT hand-wave): a section is a candidate only if normative/behavioral --
  contains behavioral verbs (guarantees, ensures, enforces, rejects,
  returns, fails, blocks, validates, is idempotent/atomic), or sits under a
  normative heading (Invariants, Guarantees, Contract, Semantics, Behavior,
  Safety, Security, Concurrency, Error handling), or is a frob:describes-
  bound module-doc behavior section. Pure narrative / overview / rationale /
  examples sections are EXEMPT. Verb + heading lists + threshold live in
  frob.toml [invariants] for per-project tuning.
- Severity ADVISORY (below warning) by default -- a nudge, not debt.
  Per-section waivable (frob:waive INV-DENSITY reason="narrative section,
  no enforceable behavior"). Project may opt-in to promote to warning.
- Anti-noise: fire once per section, never on a section with >=1 bound
  invariant, and do NOT double-count with the per-claim lint (a section that
  already trips must/must-not is handled there -- this targets the SILENT
  sections).
- Tests: fixtures for (a) behavioral section, 0 invariants -> advisory;
  (b) same + 1 bound invariant -> silent; (c) narrative section with
  behavioral-sounding prose, exempt -> silent; (d) waiver suppresses. Golden
  per TTY/plain once T-0448 lands.

Relates: per-claim invariant lint (INV001/INV002) is the complement; T-0408
(formal-vs-prose-claim coverage) is adjacent -- this is the SECTION-SILENCE
angle, not per-claim coverage.