---
id: T-3029
title: 'self-conformance (SYS100/SYS102/SYS107) red on main: ci_report.py/ci_validity.py/ghio.py
  unbound, env.read gaps'
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: medium
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SYS111 capability ratchet ceiling must be bumped in the same diff as design/frob.strata's
    new via-list sites (SYS100/SYS102/SYS107 fix); the ratchet lock is data co-dependent
    with the strata file, not a separate concern
  actor: logan
  at: '2026-08-28'
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-3019 (cluster B): tests/unit/strata/test_selfconform.py::
TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
fails on unmodified main with 23 real (non-flaky) violations, e.g.:

  SYS100 cli capability 'env.read' observed at src/frob/__main__.py:651
    but not declared
  SYS102 src/frob/ci_report.py has no node's code= glob binding it
  SYS102 src/frob/ci_validity.py has no node's code= glob binding it
  SYS102 src/frob/ghio.py has no node's code= glob binding it
  SYS107 testsuite node binds 622 file(s) (> 20), via-less 'fs.read'/
    'fs.write' may grants

src/frob/ci_report.py, src/frob/ci_validity.py, src/frob/ghio.py look
like new/renamed files with no design/frob.strata node binding them yet
(SYS102) -- likely needs a design/frob.strata update to match. The
env.read/env.write/ffi/eval capability gaps (SYS100) are smaller,
mechanical additions to existing node declarations. SYS107 needs the
oversized testsuite node's fs.read/fs.write grants narrowed with a `via`
clause or split.

Out of T-3019's own scope (src/frob/gates/_refs.py,
src/frob/check/_python.py) and design/frob.strata was leased by another
in-progress ticket (T-2989) at the time T-3019 was worked, so this
cluster B half of the original T-3019 report is split out here rather
than folded into T-3019's own scope.