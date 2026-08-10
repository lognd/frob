---
id: T-1923
title: 'post-land sweep regression from T-1916: 6 new error(s) (COV003, F401)'
state: done
kind: bug
origin: agent
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- /home/logan/projects/frob/src/frob/gates/_fix_engine_sync.py
- tickets/T-1872
- tickets/T-1895
- tickets/T-1896
- tickets/T-1900
- tickets/T-1906
- tickets/archive/T-1872/**
- tickets/archive/T-1895/**
- tickets/archive/T-1896/**
- tickets/archive/T-1900/**
- tickets/archive/T-1906/**
- tickets/T-1935/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/archive/T-1872/**
  reason: COV003 evidence rebinds for the 5 archived tickets live under tickets/archive/<id>/ticket.md
    in the v2 per-ticket ledger, and the residue draft's own file needs scope too
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tickets/archive/T-1895/**
  reason: COV003 evidence rebinds for the 5 archived tickets live under tickets/archive/<id>/ticket.md
    in the v2 per-ticket ledger, and the residue draft's own file needs scope too
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tickets/archive/T-1896/**
  reason: COV003 evidence rebinds for the 5 archived tickets live under tickets/archive/<id>/ticket.md
    in the v2 per-ticket ledger, and the residue draft's own file needs scope too
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tickets/archive/T-1900/**
  reason: COV003 evidence rebinds for the 5 archived tickets live under tickets/archive/<id>/ticket.md
    in the v2 per-ticket ledger, and the residue draft's own file needs scope too
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tickets/archive/T-1906/**
  reason: COV003 evidence rebinds for the 5 archived tickets live under tickets/archive/<id>/ticket.md
    in the v2 per-ticket ledger, and the residue draft's own file needs scope too
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tickets/T-1935/**
  reason: COV003 evidence rebinds for the 5 archived tickets live under tickets/archive/<id>/ticket.md
    in the v2 per-ticket ledger, and the residue draft's own file needs scope too
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_a_tier_a_fix_handler_with_no_detector_fails
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1916 at commit 5e17bb70a6a402747bc600c9d55c5a0414115c47 found 6 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- COV003  tickets/T-1872
- COV003  tickets/T-1895
- COV003  tickets/T-1896
- COV003  tickets/T-1900
- COV003  tickets/T-1906
- F401  /home/logan/projects/frob/src/frob/gates/_fix_engine_sync.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV003  tickets/T-1872  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1895  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1896  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1900  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1906  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- F401  /home/logan/projects/frob/src/frob/gates/_fix_engine_sync.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.