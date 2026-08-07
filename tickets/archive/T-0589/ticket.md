---
id: T-0589
title: Tie TEST001 credit to real per-symbol coverage (promote TEST005/TEST015, cross-cutting)
state: done
kind: feature
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_models.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_models.py
  reason: TestPolicy.require_branch_coverage_for_test001 new opt-in policy field
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_gates.py
  reason: evidence tests for the TEST001 promotion live here; lease was held by sibling
    T-0525 during implementation, released via requeue for landing order
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestTestGate::test_test001_zero_branch_coverage_flags_when_opted_in
- tests/test_gates.py::TestTestGate::test_test001_zero_branch_coverage_silent_when_flag_off
- tests/test_gates.py::TestTestGate::test_test001_nonzero_branch_coverage_stays_silent_when_opted_in
designated_repro_test: null
threat: null
component: null
---
T-0548 added TEST015 (WARN) reusing T-0549's existing _has_assertion_evidence heuristic to surface a public symbol whose ONLY TEST001 credit comes from a test with no assertion-shaped construct at all (docs/audits/gates-accounting.md B1's def-myfunc-pass repro). It deliberately does NOT change what TEST001 itself blocks on. This ticket is the actual cross-cutting fix the audit asked for: tie TEST001 credit to nonzero per-symbol branch coverage (frob.gates._coverage.CoverageData.symbol_branch, already computed for TEST005) or promote TEST005 to ERROR -- either requires touching TEST002/003/004/005/009's severities and interactions together, plus reconciling with the legacy-adoption WARN campaign frob.toml already documents (see its own comments), which is why it was split out rather than attempted inside T-0548. Concretely: decide whether TEST001 should require symbol_branch[record.symref] > 0 in addition to a name/edge match (requires wiring CoverageData into _test001_002, which today only sees tests: CollectedTests, not coverage), survey how many currently-green symbols would flip red (mirroring T-0547/T-0556's compat-survey precedent in this same audit pass), and land the sound subset.

TEST-pool triage (T-draft-edbf1e26, 2026-07-22): re-measured `frob check --only test` -- TEST005 and TEST015 both currently report 0 findings against this tree (fixture-pinned to `main`+T-0583, no coverage stamp present so a stale/absent stamp masking a real regression cannot be ruled out; re-verify once T-0586's committed-lock wiring lands). No genuine findings to disposition in this pass for either bucket.