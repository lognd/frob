---
id: T-3175
title: Declare component Flows for the re-exports T-3151 added to frob/__init__.py
state: dropped
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3151 added genuinely-missing re-exports to src/frob/__init__.py (ci_report, ci_validity, findings, ghio, repo_meta, doctor). Each is an undeclared cross-component import (cli -> __foreign__), so SYS003 fires on them:

  src/frob/__init__.py:38  frob.ci_report
  src/frob/__init__.py:47  frob.ci_validity
  src/frob/__init__.py:83  frob.findings

That finding raised quarantine on 2026-08-27 and, together with a DRIFT001 from T-3156, disabled deferred landing fleet-wide and timed out T-3157's land. I dismissed it as coordinator to unblock the fleet; the declarations are still OWED, which is why this ticket exists rather than the obligation living only as prose in a dismissal reason.

FIX: declare the Flow in that direction for each import, or determine that the re-export itself is wrong and remove it. Do NOT waive SYS003 to silence it -- the re-exports were real gaps worth closing, so the architecture declaration is the honest resolution.

NOTE scripts/branch_stranded_work_analysis.py:287-289 carries the same rule (scripts_ops -> graphlang) but is a separate pre-existing case; file it separately if it needs fixing, do not fold it in.

## Drop reason
- 2026-08-27: duplicate of T-3172, same two sweep-filed findings. See T-3173's drop reason.
