---
id: T-4531
title: 'post-land sweep regression from T-4515: 11 new (rule, file) identit(ies) (AFFECT001,
  COV001, COV002, COV007)'
state: done
kind: bug
origin: agent
created: '2026-09-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .git/frob-leases/T-3615.json
- .git/frob-leases/T-4493.json
- src/frob/excludes.py
- src/frob/lang/_project_detect.py
- tests/test_excludes.py
- tests/unit/test_lang_project_detect.py
findings:
- - AFFECT001
  - src/frob/lang/_project_detect.py
- - COV001
  - src/frob/excludes.py
- - COV001
  - src/frob/lang/_project_detect.py
- - COV002
  - tests/test_excludes.py
- - COV002
  - tests/unit/test_ci_self_gate_unscoped.py
- - COV002
  - tests/unit/test_lang_project_detect.py
- - COV007
  - src/frob/lang/_project_detect.py
- - DOC002
  - src/frob/lang/_project_detect.py
- - DUP002
  - tests/unit/test_lang_project_detect.py
- - TICK010
  - /home/logan/projects/frob/.git/frob-leases/T-3615.json
- - TICK010
  - /home/logan/projects/frob/.git/frob-leases/T-4493.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/unit/test_ci_self_gate_unscoped.py
  reason: collides with T-4534's in-progress lease on this file; T-4534 already covers/fixes
    its COV002 finding (same underlying work as my just-landed T-draft-357dade2/T-4532)
  actor: logan
  at: '2026-09-16'
body_changes:
- mode: append
  reason: 'BUG002 structurally untestable via pytest: gate/doc-metadata state, not
    application code'
  actor: logan
  at: '2026-09-16'
  old_length: 3631
  new_length: 4351
evidence:
- tests/unit/test_lang_project_detect.py::test_detects_unity_project
- tests/test_excludes.py::TestUnityExcludeGlobs::test_unity_project_adds_globs
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-4515 at commit 152c03b70d1e7745f233de724fa3887e81aeb60b found 11 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- AFFECT001  src/frob/lang/_project_detect.py
- COV001  src/frob/excludes.py
- COV001  src/frob/lang/_project_detect.py
- COV002  tests/test_excludes.py
- COV002  tests/unit/test_ci_self_gate_unscoped.py
- COV002  tests/unit/test_lang_project_detect.py
- COV007  src/frob/lang/_project_detect.py
- DOC002  src/frob/lang/_project_detect.py
- DUP002  tests/unit/test_lang_project_detect.py
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3615.json
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4493.json

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- AFFECT001  src/frob/lang/_project_detect.py  -> attributed to T-4515 (commit 152c03b70d1e, already closed/dropped -- filed below) via src/frob/lang/_project_detect.py::UnityProjectDetectError
- COV001  src/frob/excludes.py  -> attributed to T-4515 (commit 152c03b70d1e, already closed/dropped -- filed below) via src/frob/excludes.py::UNITY_EXCLUDE_GLOBS
- COV001  src/frob/lang/_project_detect.py  -> attributed to T-4515 (commit 152c03b70d1e, already closed/dropped -- filed below) via src/frob/lang/_project_detect.py::UnityProjectDetectError
- COV002  tests/test_excludes.py  -> attributed to T-4515 (commit 152c03b70d1e, already closed/dropped -- filed below) via tests/test_excludes.py::TestUnityExcludeGlobs
- COV002  tests/unit/test_ci_self_gate_unscoped.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  tests/unit/test_lang_project_detect.py  -> attributed to T-4515 (commit 152c03b70d1e, already closed/dropped -- filed below) via tests/unit/test_lang_project_detect.py::_make_unity_project
- COV007  src/frob/lang/_project_detect.py  -> attributed to T-4515 (commit 152c03b70d1e, already closed/dropped -- filed below) via src/frob/lang/_project_detect.py::UnityProjectDetectError
- DOC002  src/frob/lang/_project_detect.py  -> attributed to T-4515 (commit 152c03b70d1e, already closed/dropped -- filed below) via src/frob/lang/_project_detect.py::UnityProjectDetectError
- DUP002  tests/unit/test_lang_project_detect.py  -> attributed to T-4515 (commit 152c03b70d1e, already closed/dropped -- filed below) via tests/unit/test_lang_project_detect.py::_make_unity_project
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3615.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4493.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:waive BUG002 reason="post-land sweep residue: the defect is frob check GATE state (AFFECT001/COV001/COV002/COV007/DOC002/DUP002 on already-landed T-4515 commits with no open scope owner), not application behavior a pytest repro can exercise at the parent commit. Fix is doc paragraphs (docs/modules/lang.md#unity-project-detection, previously dangling), one frob:doc anchor, and removing a redundant private-symbol frob:doc directive -- none of which pytest observes. Repro is the frob check invocation: frob check --only coverage --only drift --only affect_drift --only clones --ticket T-4531 --base dev --files <the scoped files> reported these rules as errors before this change and 0 after (see Done report)."