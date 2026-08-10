---
id: T-1933
title: 'post-land sweep regression from T-1556: 3 new error(s) (ARCH001, DOC001, SEC110)'
state: queued
kind: bug
origin: agent
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/design/cli-hygiene.md
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_new.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1556 at commit 16880d5170a24b81f8c1993eaae15b2812307640 found 3 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- ARCH001  src/frob/app/ticket_runner/_close_cmd.py
- DOC001  docs/design/cli-hygiene.md
- SEC110  src/frob/app/ticket_runner/_new.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH001  src/frob/app/ticket_runner/_close_cmd.py  -> attributed to T-1556 (commit 16880d5170a2, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_close_cmd.py::_close_failure_hint
- DOC001  docs/design/cli-hygiene.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SEC110  src/frob/app/ticket_runner/_new.py  -> attributed to T-1556 (commit 16880d5170a2, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_mutate.py::_scope -> src/frob/app/ticket_runner/_new.py::_emit_scope_closure_warnings -> src/frob/app/ticket_runner/_new.py::_SCOPE_CLOSURE_WARNING_COLLAPSE_THRESHOLD

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.