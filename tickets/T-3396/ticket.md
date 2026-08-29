---
id: T-3396
title: Split src/frob/process/_reap.py under LARGE001's 800-line threshold
state: in-progress
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/process/_reap.py
- src/frob/process/_proc_scan.py
- tests/unit/test_process_reap.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/process/_proc_scan.py
  reason: T-3396's LARGE001 split moved half of _reap.py's symbols into a new sibling
    module (_proc_scan.py) and required repointing two frob:tests path directives
    in the test file that cite the old location
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_process_reap.py
  reason: T-3396's LARGE001 split moved half of _reap.py's symbols into a new sibling
    module (_proc_scan.py) and required repointing two frob:tests path directives
    in the test file that cite the old location
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
LARGE001 fires on src/frob/process/_reap.py (952 lines, threshold 800). A real split (candidate: separate the reap/wait-loop mechanics from the process-tree/orphan-detection helpers) is real engineering, not a mechanical drive-by fix, so it is deferred here following the same disposition as T-3059/T-3260 for the other LARGE001 files.