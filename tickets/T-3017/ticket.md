---
id: T-3017
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2993):
  2 new (rule, file) identit(ies), 1 finding(s) (I001, REF002)'
state: in-progress
kind: docs
origin: agent
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/yaml_io.py
- tests/test_narrative_migrate.py
findings:
- - I001
  - /home/logan/projects/frob/tests/test_narrative_migrate.py
- - REF002
  - src/frob/yaml_io.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: kind
  old_value: bug
  new_value: docs
  reason: T-3017's findings (I001 test_narrative_migrate.py, REF002 src/frob/yaml_io.py)
    no longer reproduce; reclassifying to docs-kind so the docs-kind --evidence-cmd
    channel applies to this disposition-only close
  actor: logan
  at: '2026-08-28'
body_changes:
- mode: append
  reason: record re-verification for series-DC disposition
  actor: logan
  at: '2026-08-28'
  old_length: 1409
  new_length: 1986
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2993) at commit 084ef643981fce353c2bcc988749bb106ba344a4 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- I001  /home/logan/projects/frob/tests/test_narrative_migrate.py
- REF002  src/frob/yaml_io.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- I001  /home/logan/projects/frob/tests/test_narrative_migrate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- REF002  src/frob/yaml_io.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

Re-verified on current main (2026-08-28): src/frob/yaml_io.py no longer exists -- T-2989 (landed 2026-08-26, commit 2f0d14f8a) renamed frob.yaml_io -> frob.yamlio repo-wide; the module now at src/frob/yamlio.py carries no REF002 (single-anchor) finding in a fresh gates-fast run. ruff check tests/test_narrative_migrate.py reports 'no issues' -- I001 (import sort) does not fire either. Both identities are pre-existing residue the rolling baseline had not recorded, since resolved incidentally by an unrelated rename land (T-2989), not by any fix in this ticket's own scope.