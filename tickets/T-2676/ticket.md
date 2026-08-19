---
id: T-2676
title: 'SYS107 test assertion is severity-blind: testsuite fs.read/fs.write ambient
  grants fail 3 self-conform tests even though WARN-only at the gate'
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/strata/test_selfconform.py
- tests/unit/strata/test_conform_eval_needle.py
- src/frob/strata/_selfconform.py
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
`check_self_conformance`'s raw `violations` tuple (src/frob/strata/_selfconform.py,
`_via_less_large_node_violations`) does not filter by severity -- it appends a
SYS107 finding for EVERY via-less `may` atom on a node over the file-count
threshold, regardless of whether `frob.gates._sys_selfaudit._selfaudit_severity`
would classify that atom as ERROR or WARN at the `frob check` gate layer.

T-2503 made testsuite's `fs.read`/`fs.write` grants ambient (via-less) alongside
`exec`. T-2224's SYS107_FAIL_CLOSED_ATOMS set does NOT include `fs.read`/`fs.write`
(they stay WARN-only at the gate), so `frob check --only sys` correctly reports
0 errors for them. But three tests --
tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant,
tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean,
tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
-- assert `violations == ()` directly against `check_self_conformance`'s raw
output, with no severity filter at all. So these three tests fail on
testsuite's via-less `fs.read`/`fs.write` grants even with `exec` restored to
an enumerated via-list (T-2666), and will keep failing as long as
`fs.read`/`fs.write` stay ambient per T-2503's own deliberate, disclosed
decision (which T-2666 was explicitly told not to revert).

This is a real, confirmed defect, distinct from T-2666's exec/SYS107 collision:
either these three tests need a severity-aware filter (matching what
`frob check --only sys` actually gates on), or `fs.read`/`fs.write` need their
own via-lists restored too (which would partially re-open T-2503's own
decision) -- a call for the repo owner, not a mechanical fix. Confirmed by
direct investigation: after T-2666 lands (exec via-list restored, SYS107/exec
error cleared repo-wide), all three tests still fail with exactly two
remaining SYS107 findings each: ('SYS107', 'testsuite', ..., capability='fs.read')
and ('SYS107', 'testsuite', ..., capability='fs.write').
