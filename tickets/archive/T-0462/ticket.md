---
id: T-0462
title: 'invariant-language lint: add exclusivity words (only, sole/solely, exclusively,
  nothing else, never...except, at most/exactly one) to the INV001/INV002 normative-claim
  corpus so an ''only X'' claim requires a bound invariant'
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
  reason: T-0462 gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
- op: add
  glob: pyproject.toml
  reason: REL001 bump required by adding public API (inv003_gate, find_exclusivity_claims,
    EXCLUSIVITY_CLAIM_PATTERNS)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 bump required by adding public API (inv003_gate, find_exclusivity_claims,
    EXCLUSIVITY_CLAIM_PATTERNS)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: REL001 bump required by adding public API (inv003_gate, find_exclusivity_claims,
    EXCLUSIVITY_CLAIM_PATTERNS)
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 bump required by adding public API (inv003_gate, find_exclusivity_claims,
    EXCLUSIVITY_CLAIM_PATTERNS)
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns
- tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_with_bound_known_invariant_is_silent
- tests/test_gates.py::TestInv003Gate::test_marker_naming_unknown_invariant_still_warns
- tests/test_gates.py::TestInv003Gate::test_no_exclusivity_language_is_silent
- tests/test_gates.py::TestInv003Gate::test_missing_docs_dir_is_silent
designated_repro_test: null
threat: null
component: null
---
