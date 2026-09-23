---
id: T-5168
title: 'post-land sweep regression from T-4115: 3 new (rule, file) identit(ies), 3
  finding(s) (WIRE001)'
state: queued
kind: bug
origin: agent
created: '2026-09-21'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.540.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_config_path_defaults.py
- src/frob/gates/_docarch_structural.py
- src/frob/gates/_route_response_model.py
findings:
- - WIRE001
  - src/frob/gates/_config_path_defaults.py
- - WIRE001
  - src/frob/gates/_docarch_structural.py
- - WIRE001
  - src/frob/gates/_route_response_model.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.540.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-4115 at commit 3308912248c58964e8caba3d5d43ba4537156f60 found 28 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (3), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 3 actual finding(s) across those 3 identit(ies).

New (rule, file) identit(ies) filed here:

- WIRE001  src/frob/gates/_config_path_defaults.py
- WIRE001  src/frob/gates/_docarch_structural.py
- WIRE001  src/frob/gates/_route_response_model.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC012  docs/commands/  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP001  src/frob/gates/_docarch_structural.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DUP001  tests/gates/test_docarch_structural.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- FLAGCOV001  frob.toml  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- LEXCHECK001  src/frob/gates/_docarch_structural.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF006  src/frob/gates/_config_path_defaults.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3032.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3899.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3936.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3986.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-3997.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4030.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4113.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4254.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4420.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4509.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4612.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4658.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4661.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4951.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4991.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-4993.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-5124.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-5125.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK010  /home/logan/projects/frob/.git/frob-leases/T-5126.json  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE001  src/frob/gates/_config_path_defaults.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE001  src/frob/gates/_docarch_structural.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE001  src/frob/gates/_route_response_model.py  -> attributed to T-4115 (commit 3308912248c5, already closed/dropped -- filed below) via src/frob/gates/_route_response_model.py::_HTTP_VERBS

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.