---
id: T-2456
title: land's budgeted check drops gates, so lands report verified while putting errors
  on main
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a land whose frob check was budget-truncated, when it reports, then
    it states that verification was incomplete and names the skipped gates, rather
    than presenting as a clean verification.
  evidence: []
- text: Given a branch introducing a trivial ruff E501 violation, when it is landed,
    then the violation is caught rather than reaching main silently.
  evidence: []
- text: Given a land whose check runs to completion with no findings, when it reports,
    then it lands cleanly with no added friction.
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
`frob ticket land` runs `frob check --budget 300`. A budget in this
codebase DROPS GATES rather than extending time (measured previously:
`--budget 480` ran 15 of 52 gates while the full run takes 274s). So on
a busy machine the land-time gate silently skips whole gates, reports
clean, and lands code that puts ERRORS on main.

MEASURED CONSEQUENCE, this session:

    error floor ~3 hours ago:      30
    error floor now:              119
    lands in that window:          22   (every one reporting verified=True)

Breakdown of the 119:

    70  SELFAUDIT001   (56 of them one single shape, below)
    18  COV002
    14  DRIFT002
    11  COV003
     6  SEC110
     6  TICK004
     4  ruff-check:E501
     4  RENDER001
     3  ruff-check:F401 / COV001 / DOC002 / DRIFT001

The dominant cluster is unambiguous and repeated verbatim 56 times:

    SELFAUDIT001: self-audit family SYS100 node=gates: capability
      'fs.write' observed at src/frob/gates/_dup_graph_schema.py:99
      but not declared

Those are the T-2390 config-schema children's new modules. NINE sibling
tickets each add a schema module, each module writes to the filesystem,
and none declared the `fs.write` capability in `design/frob.strata`.
Six landed before anyone noticed, three more were in flight when this
was measured. Even `ruff-check:E501` -- line-too-long, the most trivially
detectable error class that exists -- is on main four times, which is the
clearest possible proof that the land gate is not gating.

WHY THIS IS THE HIGHEST-ORDER DEFECT HERE. Every other quality mechanism
in this repo is downstream of the land gate actually running. Promoting a
rule from WARN to ERROR, adding a meta-check, burning a family down to
zero -- all of it assumes the gate blocks the land. It does not, whenever
the machine is busy enough that the budget bites. And the busier the
fleet, the fewer gates run, so quality erosion is worst exactly when
throughput is highest. The land reports `verified=True` either way, so
nothing surfaces.

Note the interaction with the forkserver leak just fixed (T-2443): while
that leak was starving the machine, land-time checks would have been
dropping the MOST gates. The floor growth from 30 to 119 overlaps that
window closely.

FIX SHAPE -- design judgement wanted:
  - A land must not report success from a budget-truncated verification.
    At minimum, a land whose check did not run every gate must say so
    loudly and record which gates were skipped (this is exactly epic
    T-2391's doctrine applied to the land path: a clean result from an
    incomplete run is not a clean result).
  - Options to weigh: raise or remove the land budget and accept slower
    lands; run the full gate set asynchronously post-land and treat a
    failure as a revert-or-ticket obligation; or keep the budget but make
    the SKIPPED-GATE SET part of the land record so the debt is visible
    and attributable rather than silent.
  - Whatever is chosen, `BUDGET001` deferral must be surfaced in the
    land's own output, not only discoverable by running `frob check`
    unbudgeted afterwards.

POSITIVE CONTROLS:
  - must-now-report: a land whose check is budget-truncated reports the
    truncation and the skipped gates, and does not present as a clean
    verification.
  - must-still-land: a land whose check runs completely and finds
    nothing still lands cleanly with no new friction.
  - must-catch: a branch introducing a trivial ruff E501 must not be
    able to land silently -- use that as the end-to-end fixture, since
    it is exactly what got through four times.
