---
id: T-1060
title: 'SYS205 v1: alpha anti-pattern, arbitrated_by code-identity, write path-scoping'
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_mode_conformance.py
- tests/unit/strata/test_mode_conformance.py
- docs/strata/host.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/strata/host.md
  reason: AFFECT001 will name docs/strata/host.md#resource-access-modes-t-0700 as
    _mode_conformance.py's affects()-closure doc; T-1060's three v0-cut closures need
    a real SYS205 v1 subsection there, mirroring the T-1025/SYS203 doc-scope precedent
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_alpha_mode_fires_reacquire_deadlock_alongside_the_guarded_pass
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_alpha_mode_single_lock_context_does_not_fire_reacquire_deadlock
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_exclusive_mode_discharges_through_an_arbitrated_by_node
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_exclusive_mode_fails_when_arbitrated_by_node_never_called
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_write_mode_discharges_inside_a_declared_path
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_write_mode_is_unrestricted_in_v0
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_write_mode_fails_outside_the_declared_path
- tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_write_mode_with_no_extractable_literal_stays_silent
designated_repro_test: null
threat: null
component: null
---
T-0701's SYS205 mode-conformance check disclosed three v0 cuts (module
docstring, src/frob/strata/_mode_conformance.py):

1. ALPHA's "upgrade-deadlock ANTI-PATTERN" (acquiring a write while
   holding a plain read lock context on the same resource) is not
   detected -- needs per-lock-variable identity across nested `with`
   blocks (which lock guards which resource), the same lock-IDENTITY
   modeling problem `frob.arch._lock_ordering`'s T-0694
   `_collect_module_locks` solves for the cyclic lock-order check.
2. ALPHA/EXCLUSIVE code-checkable arbiter support is `lock`-only --
   an `arbitrated_by NODE` arbiter has no code-level identity resolved
   in this pass (no cross-node call-graph analysis).
3. WRITE mode is unrestricted in v0 -- the mandate's "only on declared
   paths" clause needs path-level identity between a declared resource
   id and a specific file/call site, which this v0 pass does not have
   (same class of cut `_effects.py`'s own capability-conformance join
   already discloses).

Each needs real design work (lock-identity modeling, cross-node call
resolution, or a first-class capability/resource-path grammar) rather
than a quick patch -- filed as its own ticket per T-0701's Done report
rather than approximated unreliably in that pass.