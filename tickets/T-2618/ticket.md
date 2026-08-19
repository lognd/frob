---
id: T-2618
title: declared_source_prefixes/declared_project_package_name never got their promised
  lang.md anchor (T-2612 audit)
state: in-progress
kind: docs
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/lang.md
- src/frob/lang/_nodes.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/lang/_nodes.py
  reason: removing the two COV001 waivers this ticket's doc anchor discharges
  actor: logan
  at: '2026-08-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
src/frob/lang/_nodes.py::declared_project_package_name and
::declared_source_prefixes both carry COV001 waivers whose reason cited
T-2365's "live cross-worktree lease" on docs/modules/lang.md for the
duration of T-2389, and promised "a doc-anchor follow-up ticket adds
docs/modules/lang.md#declared-source-prefixes-t-2389 once that lease
clears".

T-2365 is done and T-2389 is done, but no such follow-up ticket was ever
filed (searched tickets/ for declared-source-prefixes-t-2389,
declared_source_prefixes, declared_project_package_name: only T-2389's
own ticket/done-report mention them, no doc-anchor ticket exists), and
docs/modules/lang.md still has no frob:describes anchor for either
function.

Add:
  <!-- frob:describes src/frob/lang/_nodes.py::declared_project_package_name -->
  <!-- frob:describes src/frob/lang/_nodes.py::declared_source_prefixes -->
to docs/modules/lang.md with a short paragraph (T-2195/T-2389's promoted
single-home rationale, per this file's own module docstring), then remove
both COV001 waivers.

Filed by T-2612's lease-premise audit (waiver-removal-vs-owed-work split).
