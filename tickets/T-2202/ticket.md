---
id: T-2202
title: frob check --only cycle now genuinely fails on frob's own repo once resolve_local_import
  (T-2195) resolves src-layout imports -- real cyclic-import clusters, not a fix defect
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/**
- src/frob/dup/**
- src/frob/tickets/**
- src/frob/app/**
- src/frob/serve/**
- src/frob/verify/**
- src/frob/arch/**
- src/frob/deploy/**
- src/frob/vet/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2195 finding. Fixing `resolve_local_import` (T-2195) to resolve
src-layout absolute and relative python imports makes `frob check --only
cycle` (the `frob-cycle` tool) go from "no cycles" to genuinely failing:
3 errors, 1 warning, on this repo's own `src/frob` tree.

This is NOT a defect in T-2195's fix -- these are real, previously
INVISIBLE import cycles that `resolve_local_import` returning None for
every src-layout specifier was silently hiding (confirmed directly:
reverting T-2195's fix and re-running `frob check --only cycle` reports
"no cycles" on the identical tree). Two smaller 2-node cycles are also
now visible as info-severity (`deploy/_generate.py` <->
`deploy/_generate_windows.py`, `vet/_capability.py` <->
`vet/_capability_scan.py`), plus several larger, error/warning-severity
cyclic import clusters spanning `src/frob/gates`, `src/frob/dup`,
`src/frob/tickets`/`src/frob/app/ticket_runner`/`src/frob/serve`/
`src/frob/verify`, `src/frob/arch`, and `src/frob/app`.

Untangling these is a real, separate body of work (module boundary
redesign across several packages), well outside T-2195's own scope
(`src/frob/lang/_nodes.py` + tests/docs). Filed here so the newly-true
`frob check --only cycle` failure is tracked rather than silently
regressing whichever gate/land path first turns this tool's result into
a hard gate. See T-2195's Done report for the exact before/after
`frob check --only cycle` output this finding is measured from.
