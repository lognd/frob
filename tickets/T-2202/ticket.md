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
tier: epic
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
acceptance:
- text: 'DECOMPOSE into four leaves, one per cluster -- measured from ''frob check
    --only cycle --json'', three of the four are PACKAGE-LOCAL, so the epic''s original
    nine-glob scope (gates/**, dup/**, tickets/**, app/**, serve/**, verify/**, arch/**,
    deploy/**, vet/**) is far wider than any single cluster needs and would lock most
    of the repo away from the fleet. Leaf 1 (ERROR, cross-package): graph/cache.py
    -> gates/_docblocks_refs.py -> gates/_docblocks.py -> lang/_support.py -> lang/__init__.py.
    Leaf 2 (ERROR, dup/ only): _pipeline/_smt.py, _template.py, _pipeline/_fingerprint.py,
    _pipeline/_callgraph.py. Leaf 3 (ERROR, tickets/ only): _accept.py, _setters.py,
    _land_finalize.py, _land_verify.py. Leaf 4 (WARNING, vet/ only): _hook.py, _closedworld.py,
    _scan_violations.py, _scan.py, __init__.py. Each leaf scopes to its own package
    and can be worked independently.'
  evidence: []
- text: 'These cycles are NOT new -- they were invisible until T-2195 (808e0c6fb3f4)
    fixed resolve_local_import, which had been returning None for every intra-repo
    import and made frob cycle vacuously green on frob''s own tree. Do NOT treat them
    as a regression from that land, and do NOT ''fix'' any of them by re-breaking
    import resolution. Verify the baseline before starting: frob check --only cycle
    reported 0 errors before T-2195 and 3 errors + 1 warning after.'
  evidence: []
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
