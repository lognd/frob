---
id: T-1809
title: Gate Claude-config sync drift in frob check (T-1719 item 2)
state: queued
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/**
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1719 item 2 (gate the Claude-config drift) was cut from that ticket's
own scope for two reasons: (a) it depends on the sync verb the sibling
follow-up ticket implements first (there is nothing to gate a `--check`
call against until the verb exists), and (b) `docs/modules/gates.md` and
the `_KNOWN_GATE_RULES` registry it documents were explicitly off-limits
during T-1719's dispatch window (held by other concurrent agents working
T-1773/T-1735/T-1781).

Once the sync-verb follow-up lands, add a rule (register a real, free
rule id in the `_KNOWN_GATE_RULES` registry and `docs/modules/gates.md`
-- do not invent an unregistered id) that fails `frob check` when a
managed file (per the verb's own manifest) differs from its materialized
`~/.claude/` copy. Wire it as its own `--check`-shaped gate stage,
following the existing `gate:*` family pattern in `src/frob/gates/`.
