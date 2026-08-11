---
id: T-2132
title: An unattributable time-based finding (TICK004, commit=None) can raise the verify
  quarantine, switching deferred landing OFF repo-wide and taxing every land with
  synchronous verification
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/verify/_quarantine.py
- tests/unit/verify/test_quarantine.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/verify/
  reason: narrow whole-directory scope to the single file this fix touches, per T-1866
    breadth guard
  actor: logan
  at: '2026-08-11'
- op: add
  glob: src/frob/verify/_quarantine.py
  reason: narrow whole-directory scope to the single file this fix touches, per T-1866
    breadth guard
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tests/unit/verify/test_quarantine.py
  reason: narrow whole-directory scope to the single file this fix touches, per T-1866
    breadth guard
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/modules/tickets.md
  reason: raise_quarantine's frob:doc anchor; adding the naturally-unattributable-rules
    docs section
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_a_naturally_unattributable_finding_alone_does_not_raise
- tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_an_unattributed_code_finding_still_raises
- tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_a_mixed_batch_raises_with_only_the_attributable_finding_kept
designated_repro_test: tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_a_naturally_unattributable_finding_alone_does_not_raise
threat: null
component: null
anchor: false
anchor_reason: null
---
