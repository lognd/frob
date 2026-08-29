---
id: T-3261
title: 'post-land sweep regression from T-3092, T-3079, T-3255: 4 new (rule, file)
  identit(ies), 4 finding(s) (DOCENUM001, REG008, REL001)'
state: done
kind: bug
origin: agent
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/registry/check-coverage.yaml
- docs/modules/gates.md
- strata-core/src/graph/vmodel.rs
- strata-core/src/parse/grammar_core.rs
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): doc-only fix: added rule-catalog table rows
    for F401, I001, QUEUE001, TICK014, VERSION001, VMOD001 to docs/modules/gates.md
    so the file''s own frob:enumerates directive resolves (DOCENUM001); no code changed'
  actor: logan
  at: '2026-08-29'
  old_length: 2284
  new_length: 2525
- mode: append
  reason: 'BUG002 front door (T-2393): doc-only fix: added rule-catalog table rows
    for F401, I001, QUEUE001, TICK014, VERSION001, VMOD001 to docs/modules/gates.md
    so the file''s own frob:enumerates directive resolves (DOCENUM001); no code changed'
  actor: logan
  at: '2026-08-29'
  old_length: 2525
  new_length: 2766
evidence:
- tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_claimed_member_with_doc_row_does_not_fire
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-3092, T-3079, T-3255 at commit 3d8989ac23bd0ddb0bda7181b0cc578153c6df2f found 4 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (4), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 4 actual finding(s) across those 4 identit(ies).

New (rule, file) identit(ies) filed here:

- DOCENUM001  docs/modules/gates.md
- REG008  docs/design/registry/check-coverage.yaml
- REL001  strata-core/src/graph/vmodel.rs
- REL001  strata-core/src/parse/grammar_core.rs

T-2009: 3 lands (T-3092, T-3079, T-3255) landed between the previous sweep's baseline and the commit THIS sweep actually measured (the sweep is deliberately detached, off the land critical path -- T-1684 -- so other agents' lands can land in the window before it runs). Which specific land introduced which finding below could not be determined without re-measuring at each intermediate commit; this ticket is filed against all of them rather than falsely pinned on T-3092, T-3079, T-3255 alone (the one that happened to spawn this sweep process).

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOCENUM001  docs/modules/gates.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- REG008  docs/design/registry/check-coverage.yaml  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- REL001  strata-core/src/graph/vmodel.rs  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- REL001  strata-core/src/parse/grammar_core.rs  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:no-behavior-change reason="doc-only fix: added rule-catalog table rows for F401, I001, QUEUE001, TICK014, VERSION001, VMOD001 to docs/modules/gates.md so the file's own frob:enumerates directive resolves (DOCENUM001); no code changed"

frob:no-behavior-change reason="doc-only fix: added rule-catalog table rows for F401, I001, QUEUE001, TICK014, VERSION001, VMOD001 to docs/modules/gates.md so the file's own frob:enumerates directive resolves (DOCENUM001); no code changed"