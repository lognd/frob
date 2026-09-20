---
id: T-3020
title: Register frob.narrative as a strata component; close its SELFAUDIT001/SYS003
  waivers
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: backlog
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
- src/frob/gates/_narrative_blocks.py
- src/frob/__main__.py
- docs/commands/narrative.md
- tests/test_narrative_blocks.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/commands/narrative.md
  reason: 'AFFECT001: narrative_blocks_gate''s affects()-closure doc must be touched
    in the same diff that changes the function''s body (waiver removal)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/test_narrative_blocks.py
  reason: regression test proving the SELFAUDIT001/SYS003 waivers are gone and stay
    gone
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: v0.532.0
  new_value: backlog
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-15'
- field: milestone
  old_value: v0.532.0
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-15'
evidence:
- tests/test_narrative_blocks.py::TestT3020WaiversRemoved::test_narrative_blocks_gate_has_no_selfaudit001_waiver
- tests/test_narrative_blocks.py::TestT3020WaiversRemoved::test_dispatch_narrative_has_no_sys003_waiver
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
designated_repro_test: null
acceptance:
- text: GIVEN frob.narrative's fs.read/fs.write and its cli -> narrative import WHEN
    frob check --only sys/selfaudit runs THEN neither the SELFAUDIT001 waiver on narrative_blocks_gate
    nor the SYS003 waiver on _dispatch_narrative exists in source, and both remain
    unnecessary because design/frob.strata's narrative node and cli -> narrative flow
    (T-3029) declare the capability directly
  evidence:
  - tests/test_narrative_blocks.py::TestT3020WaiversRemoved::test_narrative_blocks_gate_has_no_selfaudit001_waiver
  - tests/test_narrative_blocks.py::TestT3020WaiversRemoved::test_dispatch_narrative_has_no_sys003_waiver
  - tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
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