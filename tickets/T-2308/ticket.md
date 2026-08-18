---
id: T-2308
title: 'post-land sweep regression from T-2164: 4 new (rule, file) identit(ies), 13
  finding(s) (, E402, E501, F841)'
state: dropped
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: /home/logan/projects/frob/scripts/fleet_status.py
  reason: 'Repairing scope corruption: T-2308 was auto-filed by the post-land sweep

    generator with ABSOLUTE filesystem paths in scope (e.g.

    /home/logan/projects/frob/scripts/fleet_status.py) instead of repo-

    relative ones. This crashes EVERY `frob ticket new` invocation repo-wide

    (NotImplementedError: Non-relative patterns are unsupported, thrown from

    Path.glob inside _new.py::_expand_scope_globs_to_paths when it walks

    other queued/in-progress tickets'' scope globs for the overlap-warning

    check) -- a fleet-wide outage of ticket filing. T-1753/T-1756 have the

    same corruption but are state=done and excluded from the live overlap

    check, so they are harmless; T-2308 is queued (non-terminal) and is the

    one live offender found via a full non-terminal-state scan. Replacing the

    two absolute-path entries with their repo-relative equivalents (same

    files, same intent) restores `frob ticket new` for the whole fleet without

    changing what T-2308 actually covers. Filed under T-2331''s own emergency

    Done report (this crash blocked filing T-2331''s own child ticket).

    '
  actor: logan
  at: '2026-08-17'
- op: remove
  glob: /home/logan/projects/frob/tests/test_ticket_land.py
  reason: 'Repairing scope corruption: T-2308 was auto-filed by the post-land sweep

    generator with ABSOLUTE filesystem paths in scope (e.g.

    /home/logan/projects/frob/scripts/fleet_status.py) instead of repo-

    relative ones. This crashes EVERY `frob ticket new` invocation repo-wide

    (NotImplementedError: Non-relative patterns are unsupported, thrown from

    Path.glob inside _new.py::_expand_scope_globs_to_paths when it walks

    other queued/in-progress tickets'' scope globs for the overlap-warning

    check) -- a fleet-wide outage of ticket filing. T-1753/T-1756 have the

    same corruption but are state=done and excluded from the live overlap

    check, so they are harmless; T-2308 is queued (non-terminal) and is the

    one live offender found via a full non-terminal-state scan. Replacing the

    two absolute-path entries with their repo-relative equivalents (same

    files, same intent) restores `frob ticket new` for the whole fleet without

    changing what T-2308 actually covers. Filed under T-2331''s own emergency

    Done report (this crash blocked filing T-2331''s own child ticket).

    '
  actor: logan
  at: '2026-08-17'
- op: add
  glob: scripts/fleet_status.py
  reason: 'Repairing scope corruption: T-2308 was auto-filed by the post-land sweep

    generator with ABSOLUTE filesystem paths in scope (e.g.

    /home/logan/projects/frob/scripts/fleet_status.py) instead of repo-

    relative ones. This crashes EVERY `frob ticket new` invocation repo-wide

    (NotImplementedError: Non-relative patterns are unsupported, thrown from

    Path.glob inside _new.py::_expand_scope_globs_to_paths when it walks

    other queued/in-progress tickets'' scope globs for the overlap-warning

    check) -- a fleet-wide outage of ticket filing. T-1753/T-1756 have the

    same corruption but are state=done and excluded from the live overlap

    check, so they are harmless; T-2308 is queued (non-terminal) and is the

    one live offender found via a full non-terminal-state scan. Replacing the

    two absolute-path entries with their repo-relative equivalents (same

    files, same intent) restores `frob ticket new` for the whole fleet without

    changing what T-2308 actually covers. Filed under T-2331''s own emergency

    Done report (this crash blocked filing T-2331''s own child ticket).

    '
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'Repairing scope corruption: T-2308 was auto-filed by the post-land sweep

    generator with ABSOLUTE filesystem paths in scope (e.g.

    /home/logan/projects/frob/scripts/fleet_status.py) instead of repo-

    relative ones. This crashes EVERY `frob ticket new` invocation repo-wide

    (NotImplementedError: Non-relative patterns are unsupported, thrown from

    Path.glob inside _new.py::_expand_scope_globs_to_paths when it walks

    other queued/in-progress tickets'' scope globs for the overlap-warning

    check) -- a fleet-wide outage of ticket filing. T-1753/T-1756 have the

    same corruption but are state=done and excluded from the live overlap

    check, so they are harmless; T-2308 is queued (non-terminal) and is the

    one live offender found via a full non-terminal-state scan. Replacing the

    two absolute-path entries with their repo-relative equivalents (same

    files, same intent) restores `frob ticket new` for the whole fleet without

    changing what T-2308 actually covers. Filed under T-2331''s own emergency

    Done report (this crash blocked filing T-2331''s own child ticket).

    '
  actor: logan
  at: '2026-08-17'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-2164 at commit eadd8c7d8675239bb76b0c51ab3a66a1be1d5fb9 found 4 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (4), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 13 actual finding(s) across those 4 identit(ies).

New (rule, file) identit(ies) filed here:

-   
- E402  /home/logan/projects/frob/scripts/fleet_status.py
- E501  /home/logan/projects/frob/scripts/fleet_status.py
- F841  /home/logan/projects/frob/tests/test_ticket_land.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

-     -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E402  /home/logan/projects/frob/scripts/fleet_status.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/scripts/fleet_status.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- F841  /home/logan/projects/frob/tests/test_ticket_land.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-17: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (E402 scripts/fleet_status.py, E501 scripts/fleet_status.py, F841 tests/test_ticket_land.py) is absent from the fresh unscoped measurement at doable's deferred sweep, i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
