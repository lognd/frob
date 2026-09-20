---
id: T-4538
title: 'post-land sweep regression from T-4536: 4 new (rule, file) identit(ies) (CLAUDE001,
  COV002)'
state: dropped
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
- .claude/hooks/sync-claude-config.py
- src/frob/vet/_capability.py
- src/frob/vet/_capability_csharp.py
- src/frob/vet/_capability_scan.py
findings:
- - CLAUDE001
  - .claude/hooks/sync-claude-config.py
- - COV002
  - src/frob/vet/_capability.py
- - COV002
  - src/frob/vet/_capability_csharp.py
- - COV002
  - src/frob/vet/_capability_scan.py
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
The deferred post-land unscoped sweep (T-1684) for T-4536 at commit 7482623475c60e4c6cd9447b0b87d75e20ce55a8 found 4 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- CLAUDE001  .claude/hooks/sync-claude-config.py
- COV002  src/frob/vet/_capability.py
- COV002  src/frob/vet/_capability_csharp.py
- COV002  src/frob/vet/_capability_scan.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- CLAUDE001  .claude/hooks/sync-claude-config.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV002  src/frob/vet/_capability.py  -> attributed to T-4536 (commit 7482623475c6, already closed/dropped -- filed below) via src/frob/vet/_capability.py::_scan_file_operations
- COV002  src/frob/vet/_capability_csharp.py  -> attributed to T-4536 (commit 7482623475c6, already closed/dropped -- filed below) via src/frob/vet/_capability.py::_scan_file_operations -> src/frob/vet/_capability_csharp.py::_extra_cs_binding_operations -> src/frob/vet/_capability_csharp.py::_cs_binding_operations -> src/frob/vet/_capability_csharp.py::_cs_resolved_candidates -> src/frob/vet/_capability_csharp.py::_cs_import_table -> src/frob/vet/_capability_csharp.py::_CS_WILDCARD_DANGEROUS_NAMESPACES
- COV002  src/frob/vet/_capability_scan.py  -> attributed to T-4536 (commit 7482623475c6, already closed/dropped -- filed below) via src/frob/vet/_capability_scan.py::scan_file_capabilities

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-09-19: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (CLAUDE001 .claude/hooks/sync-claude-config.py, COV002 src/frob/vet/_capability.py, COV002 src/frob/vet/_capability_csharp.py, COV002 src/frob/vet/_capability_scan.py) is absent from a direct re-check of exactly the 824 named (rule, file) identit(ies) (not a full sweep) that completed with no failed/silent tool stage at doable's deferred sweep (T-2521: this drop only fires when that measurement itself completed -- no budget deferral, no failed/silent tool stage -- never on an unmeasured or partial run), i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
