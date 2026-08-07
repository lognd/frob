---
id: T-0383
title: 'strata: audit and populate caught_by on all existing out-of-scope/benign-capability
  entries'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0382
parent: T-0376
tier: ticket
sprint: null
scope:
- src/frob/strata/
- docs/design/registry/
- tests/unit/strata/test_threat.py
- tests/unit/strata/test_compliance.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_threat.py
  reason: 'T-0383''s checkable proof lives here: exhaustive audit test over every
    built-in caught_by entry'
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/unit/strata/test_compliance.py
  reason: T-0383's checkable proof for the compliance caught_by family
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_has_a_substantive_caught_by
- tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_passes_real_production_verification
- tests/unit/strata/test_compliance.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_has_a_substantive_caught_by
- tests/unit/strata/test_compliance.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_passes_real_production_verification
designated_repro_test: null
threat: null
component: null
---
Audit every EXISTING out_of_scope / BenignCapability / CAPABILITY_MATRIX_EXCUSES entry in the repo and populate its new caught_by field with the real compensating control, or, where nothing actually catches the excused item, convert the entry into a real enforced check instead of an excuse. Acceptance: frob check --only invariant/security passes with the caught_by verification (T-0382) enabled across the whole repo; zero entries left with a placeholder/fabricated caught_by.