---
id: T-3020
title: Register frob.narrative as a strata component; close its SELFAUDIT001/SYS003
  waivers
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
- src/frob/gates/_narrative_blocks.py
- src/frob/__main__.py
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
T-3014 wired narrative_blocks_gate into gates/__init__.py's GATE_RUNNERS dict
and removed the WIRE001 waiver, proving NARR001 reachable via
`frob check --only narrative_blocks` (121 repo-wide warnings). Two related
waivers remain, both blocked purely by design/frob.strata's lease state at
the time (T-2989 held it during T-3014's own work window too):

- SELFAUDIT001 in src/frob/gates/_narrative_blocks.py::narrative_blocks_gate
  -- needs narrative_blocks_gate's own fs.read declared on the existing
  "gates" strata node (mirroring excludehazard/refs/secrets' own fs.read
  declarations there).
- SYS003 in src/frob/__main__.py::_dispatch_narrative -- frob.narrative has
  no strata component/node of its own at all (unlike frob.refactor's "node
  refactor" + "flow f_t2403_cli_refactor : cli -> refactor"); registering
  one and adding the equivalent cli -> narrative flow is a real addition,
  not a one-line fix, and is scoped out of T-3014 on purpose.

Both fixes are small once design/frob.strata is free. Follow the T-2994
doctrine (WARN-first is not relevant here -- these are wiring-completeness
waivers, not new detectors).
