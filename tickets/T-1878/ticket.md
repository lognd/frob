---
id: T-1878
title: Document T-1868's live cross-worktree lease check for scope --add in docs/modules/tickets.md
state: in-progress
kind: docs
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
- src/frob/tickets/_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_scope.py
  reason: plan requires swapping the interim frob:todo pointer for a real frob:doc
    anchor
  actor: logan
  at: '2026-08-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
docs/modules/tickets.md was contended by T-1873 (in-progress) at the
time T-1868 landed its fix (frob.tickets._scope._scope_add_conflicts /
_scope_add_live_lease_conflict, the same lease-conflict check `frob
ticket start` runs now also applied to `scope --add`). T-1868's own
Done report carries the full explanation; this ticket is just the
follow-up to move a condensed version into docs/modules/tickets.md's
own "See also" catalog once the file frees up, with a frob:doc anchor
from src/frob/tickets/_scope.py::_scope_add_live_lease_conflict pointed
at it (currently pointed at T-1868's Done report instead, as an interim
anchor).
