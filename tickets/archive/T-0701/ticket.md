---
id: T-0701
title: 'strata mode-conformance enforcement: prove each node''s code OBEYS its declared
  access mode (read/append/write/exclusive)'
state: done
kind: security
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0700
- T-0717
parent: T-0331
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/vet/**
- tests/unit/strata/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_read_mode_fails_on_a_write_open
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_read_mode_discharges_on_read_only_code
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_append_mode_fails_on_a_truncating_write
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_append_mode_discharges_on_an_append_only_open
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_exclusive_mode_fails_on_access_outside_the_arbiter
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_exclusive_mode_discharges_inside_the_declared_lock
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_exclusive_mode_with_no_lock_declared_fails_closed
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_alpha_mode_fails_on_an_unguarded_write
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_write_mode_is_unrestricted_in_v0
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_node_with_no_access_declarations_is_never_checked
designated_repro_test: null
acceptance:
- text: GIVEN a node declaring mode=read whose bound code opens the resource for writing
    WHEN sys checks run THEN a fail-closed error names the write site; GIVEN mode=exclusive
    with an access outside the arbiter context THEN an error names the unguarded path;
    GIVEN conforming code per mode THEN each discharges
  evidence:
  - tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_read_mode_fails_on_a_write_open
threat: null
component: null
---
User mandate 2026-07-22: contention semantics are worthless unless ENFORCED -- a declared mode nothing verifies is the catalogued-is-not-enforced trap (T-0343 doctrine). For every node with code= bindings and a declared resource mode (T-0700 grammar), join the declaration against the code's OBSERVED effects (the T-0595 code-binding pattern, wired to production per T-0630; effect classification from the vet/T-0339 capability resolvers): READ = zero write-capable operations against the resource (write-mode opens, os.remove/rename, SQL DML, sends on the port) -- fail-closed on opaque access to the resource; APPEND = writes only via append-mode opens, no truncate/rewrite; ALPHA (update/upgradeable-lock intent, user-specified) = reads freely, but every observed WRITE against the resource must be provably preceded on the same path by an upgrade acquisition (alpha->write transition through the declared arbiter) -- a write reachable while still in alpha-only context fails closed; additionally the model-level alpha+alpha exclusion (at most one alpha declarant per resource) is checked at elaboration, and the code-level analysis flags the upgrade-deadlock ANTI-PATTERN (acquiring write while holding plain read on the same resource, the case alpha exists to prevent -- recommend alpha in the finding); WRITE = read+write allowed but only on declared paths (undeclared sibling access = finding); EXCLUSIVE = write conformance PLUS every observed access provably inside the declared arbiter/lease context (join T-0694's code-level lock identification with the model-level arbiter declaration; an access path outside the arbiter fails closed). Violations are SYS errors naming the node, the declared mode, and the offending observed operation. Litmus fixtures per mode, firing and clean.