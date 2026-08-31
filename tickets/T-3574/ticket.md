---
id: T-3574
title: Declare the 3 SYS111 ratchet bumps + fix T-3546 doc DOC006; extend T-3324's
  land gate to refuse diff-attributable SYS111/DOC006
state: queued
kind: bug
origin: agent
created: '2026-08-31'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
- docs/design/land-splice-test-then-impl.md
- src/frob/gates/_sys.py
- src/frob/tickets/_land_squash.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED on run 33376126399 (ubuntu-latest, HEAD ae7014517): the suite is
down to TWO failures, both residue of the newest land wave:
 1. tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
    SYS111 ratchet trips x3:
      testsuite: exec grew to 235 (ceiling 234)
      testsuite: fs.write grew to 418 (ceiling 417)
      tickets_ledger: env grew to 6 (ceiling 5)
    New sites from the T-3561/T-3569/T-3570/T-3546-era test files and the
    reconcile cache work. Declare them: run TestRealGateGreen locally,
    declare exactly what it lists in design/frob.strata, bump the three
    ratchet entries in docs/design/registry/capability-via-ratchet.lock.json
    with reasons + this ticket id (T-3465/T-3484 pattern).
 2. tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo
    DOC006 at docs/design/land-splice-test-then-impl.md:75 -- an
    illustrative dotted symbol pointer in T-3546's design doc that does
    not resolve. Reword/backtick per the established idiom (the
    windows-portability.md precedent) or point it at the real symbol.

STRUCTURAL HALF (same ticket, same land if scope allows): this exact
whack-a-mole (new test files/docs land -> next CI run trips SYS111/DOC006)
has now cost FIVE full CI cycles. T-3324 landed "landing-time enforcement
of the live-repo self-conformance tests" (src/frob/gates/_sys.py +
_land_squash.py) yet none of these trips were refused at land. Read
T-3324's gate: if it checks only SYS100/SELFAUDIT undeclared-capability
findings and not SYS111 ratchet growth or DOC006 doc-pointer findings
attributable to the diff's own files, EXTEND it to refuse on those two
families too (diff-scoped, same mechanism), so this class dies at land
time instead of on main. If extending is too large for this ticket, land
the declarations + doc fix and file the extension with your findings on
why T-3324 missed these.
ACCEPTANCE: both tests pass locally 3x, and the Done report states
exactly why T-3324's gate did not catch these trips.
