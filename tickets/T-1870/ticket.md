---
id: T-1870
title: 'Delete frob sys sync-interface: interface= must be declared intent, not an
  auto-measured mirror nothing reads'
state: queued
kind: feature
origin: human
created: '2026-08-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/_sync_interface.py
- src/frob/gates/_fix_engine_sync.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/_cli_parsers/_misc.py
- src/frob/_cli_parsers/_design.py
- src/frob/app/sys_runner.py
- src/frob/app/config.py
- docs/commands/sys.md
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
OWNER DIRECTIVE, 2026-08-08: "sync-interface shouldn't be a thing; it
should be removed. We're making strata actually an enforcement layer
instead of dumb useless accounting."

`frob sys sync-interface` (T-1150) mechanically MEASURES every node's
bound-code public surface and WRITES it into `design/frob.strata`'s
`interface=` attributes. The design file therefore MIRRORS the code
instead of CONSTRAINING it, which inverts the entire point of a design
layer. A declaration that is auto-derived from the thing it supposedly
governs cannot govern anything.

MEASURED, and this is the damning part:

    grep for readers of `.interface` across src/frob/strata/ and
    src/frob/gates/, excluding the sync machinery itself: ZERO HITS.

Nothing consumes `interface=` for enforcement. The full lifecycle is a
closed loop with no exit:

    1. `sync-interface` measures the real public surface
    2. it writes that measurement into `interface=`
    3. SYS104 checks that the written value still matches the measurement
    4. `fix_sys104_interface_union` (a Tier-A handler) auto-repairs any
       drift, by re-measuring

Measure reality, write reality down, check the writing matches reality,
auto-fix it when it does not. No step can ever fail in a way that means
anything about the code being wrong. This is the exact shape of the
"catalogued is not enforced" failure this repo has already paid for.

IT ALSO CAUSES ACTIVE HARM. `_sync_interface_pre_land_step`
(`src/frob/app/ticket_runner/_land_cmd.py:190`) runs it AUTOMATICALLY on
every land. So an unrelated ticket's land silently rewrites
`design/frob.strata`, which then trips SCOPE001/COV002 and forces the
implementer to scope-add a globally-contended shared file. That chain
was reproduced first-hand during T-1648 and is the confirmed root cause
behind T-1868's double-lease incident. Deleting this verb IS T-1868's
requirement 3 -- remove the pressure, do not build a mechanism to manage
it.

DELETE, do not deprecate:

- `src/frob/strata/_sync_interface.py` (484 lines) -- entirely
- the interface half of `src/frob/gates/_fix_engine_sync.py` (796 lines;
  it ALSO handles COV002 and `_sync_may`, so this is a partial removal,
  not a file delete -- read it before cutting)
- `_sync_interface_pre_land_step` and its call in `_land_cmd.py`
- `fix_sys104_interface_union` and the SYS104 Tier-A registration
- the SYS104 rule itself, plus its `_KNOWN_GATE_RULES` entry and the
  `frob:enumerates` member list in `docs/modules/gates.md` (these two
  must stay in sync or DOCENUM001 fires)
- CLI surface: `frob sys sync-interface` and its `--check` flag in
  `src/frob/_cli_parsers/_misc.py` and `_design.py`; `sys_command` /
  `sys_check` fields in `src/frob/app/config.py`; the runner in
  `src/frob/app/sys_runner.py`
- docs: `docs/commands/sys.md`, `docs/strata/surface.md`,
  `docs/modules/gates.md`, `docs/guides/agent-playbook.md`, and
  `design/frob.strata`'s own self-model

EXPLICITLY OUT OF SCOPE: `src/frob/strata/_sync_may.py` (707 lines,
capability `may=` sync). It is arguably the same anti-pattern, but the
directive named `sync-interface` and `may=` capability enforcement is
live work under T-1623/T-1628. Do not touch it. If removing the
interface half forces a shared-helper decision, extract rather than
delete, and say so.

WHAT REPLACES IT: nothing, here. `interface=` becomes a HAND-DECLARED
statement of INTENDED surface. Making it enforce -- flagging a public
symbol that is NOT declared, which is the check that actually has teeth
-- is T-1629 ("interface= should declare INTENDED surface, not mirror
every public symbol"), already raised to high priority by the owner.
This ticket removes the mirror; T-1629 adds the constraint. Landing this
one first is correct and leaves `interface=` inert in between, which is
strictly better than actively lying.

SEQUENCING: this touches `docs/modules/gates.md` and `design/frob.strata`,
both heavily contended. Consider `frob ticket runs-last` if the fleet is
busy. Expect a large DEAD001 sweep after the cut -- that is the point;
fix findings in touched code rather than waiving them.
