---
id: T-0883
title: 'fix TICK006: T-0738 Done report cites phantom draft ticket T-draft-427ffd5a'
state: dropped
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Found while working T-0711: `frob check --only gates-fast` (TICK006, gate:TICK)
reports T-0738's Done report claims a filed ticket T-draft-427ffd5a that
resolves to no block in tickets.md or tickets-archive.md -- a phantom
filing trail (the T-0707/T-0615 incident class). This surfaced only after
merging main forward into a T-0711 worktree (T-0738 itself is unrelated to
T-0711's scope: src/frob/stats/**, src/frob/perf/**, tests/unit/perf/,
docs/modules/perf.md). Needs: either the real ticket T-draft-427ffd5a
resolved/filed for real, T-0738's Done report corrected to name the real
id, or an honest disclosed-historical-draft-loss waiver.

## Drop reason
- 2026-07-23: obsolete: the TICK006 it tracks was fixed on main in c2dde825 (T-0738 report retargeted to refiled T-0877) before this draft renumbered