---
id: T-3599
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3077):
  2 new (rule, file) identit(ies) (COV003, WIRE002)'
state: dropped
kind: bug
origin: agent
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_fix_engine_journal.py
- tests/unit/test_wire001_multiprocessing_target.py
findings:
- - COV003
  - tests/unit/test_wire001_multiprocessing_target.py
- - WIRE002
  - tests/unit/test_fix_engine_journal.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: record measurement before requesting drop
  actor: logan
  at: '2026-08-31'
  old_length: 1595
  new_length: 3224
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3077) at commit 60a5061856048429dc11362b590dd1ab5574ab43 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- COV003  tests/unit/test_wire001_multiprocessing_target.py
- WIRE002  tests/unit/test_fix_engine_journal.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV003  tests/unit/test_wire001_multiprocessing_target.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE002  tests/unit/test_fix_engine_journal.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

MEASURED (implementer KK, 2026-08-31): ran a fresh scoped frob check --ticket T-3599 --only gates in a rebuilt worktree at HEAD. Neither finding reproduces: (1) COV003 on tests/unit/test_wire001_multiprocessing_target.py -- T-3576's own 3 designated evidence node ids all collect cleanly (verified directly against .frob/pytest-collect.json and a live pytest --collect-only run); no other ticket cites this file's tests as evidence; the live gate:COV error list (4 unwaived errors repo-wide) contains none referencing this file. (2) WIRE002 on tests/unit/test_fix_engine_journal.py -- a direct frob.graph.dsl.parse_directives() call against this file's current content finds ZERO WAIVE edges and zero malformed directives (T-3576's done-report confirms the file's frob:waive WIRE001 on _write_journal_and_block was deliberately removed once the analyzer was taught to resolve multiprocessing.Process(target=...)); gate:WIRE (rule family WIRE) does not even appear in the tool summary, meaning zero violations AND zero waived entries repo-wide for that family. Both test files' own 12 tests pass (uv run pytest tests/unit/test_wire001_multiprocessing_target.py tests/unit/test_fix_engine_journal.py -- 12 passed). CONCLUSION: both identities are stale/non-reproducing, consistent with T-3599's own attribution note (UNATTRIBUTED, candidate commits: []) and the sweep's own caveat that the identity count is not independently re-measured -- most likely a snapshot taken mid-fleet while T-3576/T-3558 were still landing in the same wave. No code change made; nothing in scope to fix. Recommend drop as non-reproducing sweep noise.

## Drop reason
- 2026-08-31: Non-reproducing sweep noise: KK measured both identities at HEAD -- COV003 evidence nodes collect cleanly, WIRE002 waiver removal was deliberate in T-3576, gate:WIRE zero repo-wide. Snapshot raced the T-3576/T-3558 landing wave. Full measurement appended to ticket body.
