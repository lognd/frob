---
id: T-3364
title: 'Fix gate:REG002/REF002 errors: register 3 missing gate rule ids, waive REF002
  on 3 single-consumer support-module docs'
state: in-progress
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/ci_report.md
- docs/modules/ci_validity.md
- docs/modules/ghio.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/_waive.py
  reason: T-3295 holds a live in-progress lease on this exact file; splitting the
    REG002 _waive.py fix into its own ticket to land later, keeping this ticket to
    the REF002 doc-only fix which has no lease collision
  actor: logan
  at: '2026-08-29'
body_changes:
- mode: append
  reason: 'BUG002: no genuine before/after repro exists for a doc-comment-only diff;
    declaring no-behavior-change per BUG002 remedy (2)'
  actor: logan
  at: '2026-08-29'
  old_length: 1409
  new_length: 1675
- mode: append
  reason: 'BUG002: no genuine before/after repro exists for a doc-comment-only diff;
    declaring no-behavior-change per BUG002 remedy (2)'
  actor: logan
  at: '2026-08-29'
  old_length: 1675
  new_length: 1941
evidence:
- tests/test_refs_gate.py::TestMarkdownWaive::test_ref002_on_md_doc_suppressed_by_inline_waive
- tests/test_refs_gate.py::TestMarkdownWaive::test_ref002_on_md_doc_without_waive_still_fires
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Sub-ticket of T-3343 (triage). Fixes gate:REG (3->0) and gate:REF (3->0), measured via frob check --only release --only registry --only refs --json:

REG002 (3): docs/design/registry/check-coverage.yaml's CHK-GATE-VERSION001/CHK-GATE-TDD001/CHK-GATE-VMOD001 entries correctly assert 'VERSION001/TDD001/VMOD001 is a live, enforced gate rule' -- and they are (frob.gates._version_coupling.py, frob.gates._tdd_order.py's RULE_TDD001, frob.gates._vmodel.py all emit these rule ids). The doc registry was right; src/frob/gates/_waive.py's _KNOWN_GATE_RULES frozenset (REG002's known_rules cross-check set) was simply missing all three. Added them.

REF002 (3): docs/modules/ci_report.md/ci_validity.md/ghio.md each document exactly one small, single-purpose support module with exactly one real consumer by design -- inventing a second consumer would be manufactured busywork, not a genuine fix. Added frob:waive REF002 with a reason to each, matching the existing precedent in docs/audits/branch-stranded-work-2026-08-25.md and docs/design/test005-ratchet-schedule.md (same 'deliberately singly-anchored, a second consumer would not be genuine' shape).

gate:REL's 5 REL001 findings (frob:debt on open tickets T-3059/T-3260/T-3252) are separately reported: each names real, substantial implementation work (splitting oversized files, deduplicating a test helper) that should not be rushed as part of gate cleanup.

frob:no-behavior-change reason="doc-only fix: adds a frob:waive REF002 HTML-comment directive to three docs, no code, gate logic, or test file touched. The cited evidence tests exercise the pre-existing frob:waive REF002 mechanism this fix relies on (unmodified)."

frob:no-behavior-change reason="doc-only fix: adds a frob:waive REF002 HTML-comment directive to three docs, no code, gate logic, or test file touched. The cited evidence tests exercise the pre-existing frob:waive REF002 mechanism this fix relies on (unmodified)."