---
id: T-3388
title: 'SELFAUDIT001: refactor node exec via-list has no ratchet lock entry'
state: done
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
- docs/design/registry/capability-via-ratchet.lock.json
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: DOC003 (docs/commands/sys.md THREAT003 CWE-78:refactor obligation) is discharged
    in design/frob.strata itself, in the same assume-block pattern as core/checker/verify/serve
    -- this obligation only became live because this ticket's own SELFAUDIT001 fix
    (the refactor::exec ratchet entry) confirms the exec grant is real and current,
    so it belongs with this fix rather than a separate ticket
  actor: logan
  at: '2026-08-29'
body_changes:
- mode: append
  reason: 'BUG002 waiver: fix is a declaratory config/model correction, real repro
    test confounded by unrelated T-3350/T-3413 regression on main'
  actor: logan
  at: '2026-08-29'
  old_length: 1056
  new_length: 2003
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves
designated_repro_test: null
evidence_changes:
- old_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
  new_node: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves
  reason: test_sys_gate_zero_violations now fails on main due to an unrelated T-3350
    regression (nodeid.py undeclared, filed T-draft-a220ec84) -- not this ticket's
    own code; test_every_claim_proves still exercises this ticket's own weakness:CWE-78:refactor
    assume/discharge closure and passes cleanly against merged main
  actor: logan
  at: '2026-08-29'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: ae4832063e2da70372fa00137a99cb12d8386060
---
gate:SELFAUDIT (SELFAUDIT001) reports:

  self-audit family SYS111 node=refactor: exec via-list on refactor grew
  to 1 site(s), above the committed ratchet ceiling of 0

design/frob.strata already declares (with an explanatory comment around
line 1035-1039) may "exec" via "src/frob/refactor/_verify.py"; on the
refactor node, but docs/design/registry/capability-via-ratchet.lock.json
has no "refactor::exec" entry at all, so it defaults to a ceiling of 0.
This is pre-existing drift, unrelated to T-3386 (testsuite node fix) --
confirmed by git log on both files showing no recent touch to the
refactor node's exec declaration.

Fix: add a "refactor::exec" entry to the ratchet lock with
accepted_count=1 and a real reason, same shape as other entries (see
"testsuite::exec" for the pattern), OR determine whether refactor's exec
grant should be removed/tightened instead.

Filed while working T-3386 (SUPPRESS001/SELFAUDIT001 gate-visibility
sprint); do not fix inside T-3386, which is scoped to design/frob.strata
plus the testsuite ratchet entry only.

frob:waive BUG002 reason="this ticket adds a missing ratchet-lock entry (docs/design/registry/capability-via-ratchet.lock.json) plus a threat-model discharge assume (design/frob.strata) -- a declaratory config/model correction, not a code-behavior defect with a natural fail-then-pass unit test. The one test that DOES fail-then-pass on this exact fix (tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations) is now confounded post-merge by an unrelated T-3350 regression on main (src/frob/nodeid.py undeclared, tracked T-3413/T-draft-a220ec84) that trips the same zero-violations assertion for a different reason -- so it cannot currently prove THIS fix specifically without also depending on that separate, already-tracked defect being fixed first. test_every_claim_proves (bound as evidence) directly exercises the frob:claims/assume closure this fix adds and passes against the real repo." follow_up="T-3413"