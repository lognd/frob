---
id: T-1656
title: 'LARGE001 remainder: 48 files after T-1651 (3 waived, seams found for 3, 2
  flagged risky, 43 unexamined)'
state: queued
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/**
- design/frob.strata
- tests/**
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Successor to T-1651. T-1651 waived LARGE001 on 3 files (config.py,
gates/_waive.py, tickets/_models.py -- see its Done report for the
per-file "no honest seam" reasoning) and gate:LARGE moved 53 -> 50
warnings. 48 files remain over the 800-line frob.toml threshold.

Edit-frequency ranking (git log --format=%H --name-only -400, not raw
size -- see T-1651's Done report for the full method and why it
disagrees with a size-only ordering):

Real-seam split candidates identified but NOT attempted (each is its
own multi-session project per T-1646/T-1651 precedent):

1. src/frob/gates/__init__.py -- 79 edits, 7639 lines. Section-divider
   comments already group functions by gate family (DRIFT/AFFECT/COV001
   -COV007/etc). Highest-value target in the whole family.
2. src/frob/tickets/_store.py -- 25 edits, 2230 lines. Docstring names
   two backends ("single" ledger vs legacy "dir"/v2); the v2-specific
   function cluster is a distinct consumer set (legacy-layout repos).
3. src/frob/strata/_selfconform.py -- 23 edits, 1925 lines. Docstring
   documents SYS100-SYS107 as 8 distinct numbered rules, same
   rule-family seam shape as (1).

Flagged high-risk, needs dedicated investigation before deciding
split-vs-waive (already multiply split, orchestrator-shaped -- a rushed
cut risks the exact "arbitrary halves, worse than the warning" outcome
this family's own instructions warn against):

4. src/frob/tickets/_land.py -- 36 edits, 2820 lines. Already split
   3 ways (T-1186, T-1334); its own docstring names 3 retained groups
   (lock/repair-marker machinery, land()/_land_locked orchestrator,
   pre-merge preflight validators) that COULD be a 4th split but risk is
   high given this module's landing-critical role.
5. src/frob/app/ticket_runner/_land_cmd.py -- 35 edits, 2556 lines. Not
   yet examined in detail; do that first.

Everything below rank 5 (43 more files) has not been examined at all --
apply the same per-file judgement T-1651/T-1646 both used: find the real
seam (cohesive responsibility, pipeline phase, distinct consumer set) or
waive with a specific reason naming what was actually checked. A
line-count-only split is strictly worse than the warning; do not force
one to move the number.

Also carries forward one unfixed finding from T-1651 (out of its scope,
noted so it is not lost): src/frob/tickets/_land_merge_zones.py's
"known-gate-rules T-1002" union-zone glob names
src/frob/gates/__init__.py but the actual _KNOWN_GATE_RULES marker pair
lives in src/frob/gates/_waive.py -- the merge-conflict auto-resolver for
that hotspot currently cannot match at all. Worth its own small ticket if
nobody has filed one already.

Side effects every split in this family has produced (per the T-1651/
T-1646 dispatch brief) -- anticipate per split, do not discover at land
time: a new module needs a design/frob.strata code= glob addition plus
`frob sys sync-interface`; prose separated from its frob:invariant anchor
needs the anchor (or its waiver) carried forward explicitly as
carried-forward, not a new claim.