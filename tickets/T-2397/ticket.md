---
id: T-2397
title: Wire find_dropped_cli_flags into frob check as a gate (T-2387 visibility gap)
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/**
- src/frob/check/**
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2387 fixed the second occurrence of the "argparse dest has a matching
AppConfig field but is missing from a forwarding tuple" bug class
(T-0749 fixed the first, --accepts). Both times the only thing that
caught it was a human noticing broken behavior -- the detector that
would have caught it mechanically, find_dropped_cli_flags (T-2004,
src/frob/app/_config_external.py), already existed both times and was
never wrong; it was simply never wired to run anywhere except its own
unit test (tests/unit/test_app_config_flag_coverage.py::
TestFindDroppedCliFlags::test_current_tree_has_zero_dropped_flags).

A unit test nobody runs outside `pytest tests/unit/` is not an
enforcement surface -- it does not fire in `frob check`, so an agent or
operator who runs the gate-oriented workflow this repo standardizes on
never sees it. Wire find_dropped_cli_flags into frob check as its own
gate (or fold it into an existing app/config-consuming gate family)
so a new dropped-flag regression shows up the same way COV/WIRE/DEAD
findings do, not only when someone happens to run the full unit suite
or hits the bug manually in production use.

Filed per T-2387's coordinator instruction: "ask what would have made
this visible within a day, and if the answer is a frob check gate
rather than a unit test nobody runs, say so ... even if wiring it is a
separate ticket."
