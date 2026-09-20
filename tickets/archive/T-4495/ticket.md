---
id: T-4495
title: 'SYS100 testsuite via-lists enumerate every exec/fs.write test file by name:
  each new test file costs a land refusal plus a hand edit to design/frob.strata'
state: done
kind: ux
origin: agent
created: '2026-09-15'
priority: high
parent: T-3611
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
- tests/unit/strata/test_selfconform.py
- src/frob/strata/_effects.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata
  reason: narrow to the via/ratchet matching module actually touched
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/strata/_effects.py
  reason: narrow to the via/ratchet matching module actually touched
  actor: logan
  at: '2026-09-16'
evidence:
- tests/unit/strata/test_selfconform.py::TestTestsuiteViaGlobRatchet::test_new_test_file_matching_glob_via_needs_no_strata_edit
- tests/unit/strata/test_selfconform.py::TestTestsuiteViaGlobRatchet::test_non_test_node_exec_still_fails_closed
- tests/unit/strata/test_selfconform.py::TestTestsuiteViaGlobRatchet::test_testsuite_glob_growth_auto_accepts_and_writes_lock
designated_repro_test: null
acceptance:
- text: GIVEN a new tests/**.py file that spawns a subprocess or writes under tmp_path
    WHEN the land's SELFAUDIT001 SYS100 self-audit runs THEN it passes without a hand
    edit to design/frob.strata, because the testsuite node's exec and fs.write grants
    are declared by a glob or derived from the test binding
  evidence:
  - tests/unit/strata/test_selfconform.py::TestTestsuiteViaGlobRatchet::test_new_test_file_matching_glob_via_needs_no_strata_edit
- text: GIVEN a NON-test file that newly execs WHEN the self-audit runs THEN it still
    fails closed as today
  evidence:
  - tests/unit/strata/test_selfconform.py::TestTestsuiteViaGlobRatchet::test_non_test_node_exec_still_fails_closed
- text: GIVEN a testsuite glob-form via grant with no lock entry WHEN capability_ratchet_violations
    runs THEN growth auto-accepts and writes a fresh lock entry with reason 'testsuite
    glob growth' instead of raising a violation, and a non-testsuite node's bare-glob
    via still ratchets the ordinary fail-closed way
  evidence:
  - tests/unit/strata/test_selfconform.py::TestTestsuiteViaGlobRatchet::test_testsuite_glob_growth_auto_accepts_and_writes_lock
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-15: two READY tickets (T-4492, T-4414) were refused at land with 'SELFAUDIT001: self-audit family SYS100 node=testsuite: capability exec/fs.write observed at tests/unit/<new_test>.py:N but not declared'. design/frob.strata line ~1693 lists ~330 test files by name under may exec via ..., and a second list under fs.write. T-2666 chose the enumerated list because T-2224 makes via-less exec ERROR on nodes over 20 files. Owner doctrine (automatic over commands): a declaration every ticket must repeat by hand is friction to systematize. Options: a via glob (tests/**) accepted for the testsuite node only; or derive the via list from the frob:tests binding at check time. Keep fail-closed behaviour for non-test nodes.