---
id: T-2341
title: Fix 19 genuinely-new gate findings from T-2299/T-2331 sweep (ARCH001/ARCH103/COV001/COV003/DOC001/DOC002/PERF004/SELFAUDIT001/TICK004/WIRE003)
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- src/frob/app/telemetry.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/verify_runner.py
- src/frob/tickets/_land_git_ops.py
- src/frob/verify/_quarantine.py
- docs/commands/release.md
- docs/modules/cli.md
- docs/guides/coordinator-scripts.md
- design/**
- tickets.md
- tickets/T-1205
- tickets/T-1235
- tickets/T-1397
- tickets/T-1526
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Re-measurement of T-2331 (post-land sweep regression from T-2299, filed
2026-08-17 20:27) against the CURRENT floor (2026-08-17, post T-2290/
T-2310/T-2317/T-2324 watermark fix): 27 of the 32 claimed (rule, file)
identities genuinely reproduce; 5 are stale (see T-2331's Done report for
the full method and the stale list). Of the 27 real ones, 8 are already
attributed by the sweep's own reachability analysis to OTHER, already-
closed/dropped tickets (T-2242, T-2310, T-2298, T-2178) -- those are
folded into those tickets' own residue, not this one.

This ticket tracks the remaining 19 genuinely-new, UNATTRIBUTED identities
that need real code changes, not a quick fix -- several are architecture-
complexity gates (ARCH001/ARCH103) that require restructuring function
bodies, not a one-line change:

ARCH001 (extract-or-simplify, function too entangled):
- src/frob/app/telemetry.py:189
- src/frob/app/ticket_runner/_land_cmd.py:1969,2995,3443 (3 sites)
- src/frob/app/ticket_runner/_new.py:474

ARCH103 (mixes I/O + string-formatting + branching in one body):
- scripts/fleet_status.py:1549
- src/frob/app/ticket_runner/_land_cmd.py:3515,3599

COV001 (missing frob:tests edge on a touched public symbol):
- scripts/fleet_status.py:119,120,1686
- src/frob/tickets/_land_git_ops.py:1199
- src/frob/verify/_quarantine.py:471

COV003 (ticket file missing required coverage/evidence linkage):
- tickets/T-1205
- tickets/T-1235
- tickets/T-1397
- tickets/T-1526

DOC001 (broken/missing doc anchor):
- docs/commands/release.md

DOC002 (missing frob:doc edge on a touched public symbol):
- scripts/fleet_status.py:1675,1960
- src/frob/app/verify_runner.py:268

PERF004 (missing/stale perf directive):
- src/frob/app/ticket_runner/_land_cmd.py:3494
- src/frob/app/ticket_runner/_new.py:984

SELFAUDIT001 (design self-audit, 21 findings under a single `design`
identity -- needs its own investigation into what design/frob.strata
content is drifting):
- design (21 findings, `frob check --only sys` for detail)

TICK004 (ledger-consistency, 9 errors + 17 warnings under one identity):
- tickets.md

WIRE003 (wiring/reachability gap):
- docs/modules/cli.md

Plan: triage each rule family separately -- ARCH001/ARCH103 need actual
refactoring of the named functions (extract helpers, reduce branching);
COV001/COV002/DOC001/DOC002 need frob:tests/frob:doc directives added at
the named symbols; COV003 needs the four named tickets' evidence/coverage
brought into compliance with whatever COV003 currently demands; TICK004
and SELFAUDIT001 need their own read of `frob check --only tickets --only
sys` output to see the full finding text before deciding a fix, since both
collapse many findings into one (rule, file) identity here.

Do NOT force a quick fix through ARCH001/ARCH103 -- these are architecture
gates that reward a genuine decomposition, not a suppression. If a finding
turns out to be a false positive on inspection, waive it with a specific
reason (frob:waive RULE reason="..."), never blanket.
