---
id: T-3027
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3011):
  1 new (rule, file) identit(ies), 3 finding(s) (E501)'
state: done
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
- src/frob/narrative/_cli.py
findings:
- - E501
  - /home/logan/projects/frob/src/frob/narrative/_cli.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: kind
  old_value: bug
  new_value: docs
  reason: T-3027's E501 finding on src/frob/narrative/_cli.py no longer reproduces;
    reclassifying to docs-kind so the docs-kind --evidence-cmd channel applies to
    this disposition-only close
  actor: logan
  at: '2026-08-28'
body_changes:
- mode: append
  reason: record re-verification for series-DC disposition
  actor: logan
  at: '2026-08-28'
  old_length: 1244
  new_length: 1553
- mode: append
  reason: 'BUG002 front door (T-2393): E501 identity on src/frob/narrative/_cli.py
    does not reproduce on current main; ruff lint reports no E501 findings and a manual
    line-length scan confirms every line is within limit. Pre-existing residue, no
    fix required.'
  actor: logan
  at: '2026-08-28'
  old_length: 1553
  new_length: 1808
evidence:
- cmd:awk '{if(length($0)>88) c++} END{print "long_lines="c+0; exit (c>0)}' src/frob/narrative/_cli.py
  exit=0 sha256=c6821fa9620d
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3011) at commit 76c3481b5d4b1a683aa241d1e253f42ecca95301 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 3 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- E501  /home/logan/projects/frob/src/frob/narrative/_cli.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- E501  /home/logan/projects/frob/src/frob/narrative/_cli.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

Re-verified on current main (2026-08-28): ran 'frob check --only lint' (ruff) against src/frob/narrative/_cli.py -- no E501 findings. Manual line-length scan confirms every line is <=88 chars (max observed well under the limit). Pre-existing residue the rolling baseline had not recorded; not a live defect.

frob:no-behavior-change reason="E501 identity on src/frob/narrative/_cli.py does not reproduce on current main; ruff lint reports no E501 findings and a manual line-length scan confirms every line is within limit. Pre-existing residue, no fix required."