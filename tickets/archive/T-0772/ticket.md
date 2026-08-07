---
id: T-0772
title: 'capability modes phase 2: wire net.connect/net.listen, env.read/env.write,
  proc.spawn, ffi.call live + sibling-repo migration'
state: dropped
kind: security
origin: agent
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability_modes.py
- src/frob/strata/_effects.py
- src/frob/strata/_selfconform.py
- tests/unit/vet/test_capability_modes.py
- tests/unit/strata/test_effects.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN a node declaring may net.connect WHEN only listen behavior is observed
    THEN conformance fails narrowly per mode; GIVEN existing bare may net/env/proc/ffi
    declarations THEN they keep discharging coarsely until migrated with no spurious
    SYS101 staleness; GIVEN sibling repos with legacy declarations THEN a documented
    migration path exists
  evidence: []
threat: null
component: null
---
Refile of T-draft-3e4b416a, which T-0717's land dropped from the ledger (the T-0577 land-drops-drafts splice regression -- also note T-draft-32e61ad6 was dropped in the same land; that one proposed declaring may exec on graphlang for the _concurrency.py docstring false-positive and is deliberately NOT refiled: superseded by T-0769 observer fix + mitigation commit). T-0717 shipped the full mode vocabulary (FAMILY_MODES has all five families) but only wired fs live via WIRED_MODE_FAMILIES, because exploding an unwired family live would have produced spurious SYS101 staleness on every existing bare may net/env declaration. Phase 2: wire the remaining families one at a time with per-family staleness-window handling, then the sibling-repo (ESTATE) migration.

## Drop reason
- 2026-07-22: accidental duplicate: filed as a refile believing T-0717's land dropped draft 3e4b416a, but the land renumbered it to T-0771; T-0771 is the canonical phase-2 modes ticket (absorbed by T-0771)