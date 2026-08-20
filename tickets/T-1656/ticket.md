---
id: T-1656
title: 'LARGE001 remainder: 48 files after T-1651 (3 waived, seams found for 3, 2
  flagged risky, 43 unexamined)'
state: done
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
- src/frob/app/check_runner.py
- src/frob/app/sys_runner.py
- tests/test_arch_gate.py
evidence_scope:
- tests/test_arch_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/**
  reason: 'T-1656 batch 1: narrow to the 2 files examined+waived this pass; 82-file
    remainder needs the same per-file judgement, tracked back on the original ticket
    for a future batch'
  actor: logan
  at: '2026-08-19'
- op: remove
  glob: tests/**
  reason: 'T-1656 batch 1: narrow to the 2 files examined+waived this pass; 82-file
    remainder needs the same per-file judgement, tracked back on the original ticket
    for a future batch'
  actor: logan
  at: '2026-08-19'
- op: remove
  glob: docs/modules/gates.md
  reason: 'T-1656 batch 1: narrow to the 2 files examined+waived this pass; 82-file
    remainder needs the same per-file judgement, tracked back on the original ticket
    for a future batch'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/check_runner.py
  reason: 'T-1656 batch 1: narrow to the 2 files examined+waived this pass; 82-file
    remainder needs the same per-file judgement, tracked back on the original ticket
    for a future batch'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: 'T-1656 batch 1: narrow to the 2 files examined+waived this pass; 82-file
    remainder needs the same per-file judgement, tracked back on the original ticket
    for a future batch'
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/test_arch_gate.py
  reason: 'T-1656: binds existing test_large_file_fires_large001_warn as evidence
    for the gate:LARGE mechanism the two waivers this ticket added rely on; citation
    leases the file per repo convention'
  actor: logan
  at: '2026-08-19'
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): Batch-1 outcome: 2 files disposed (real per-file
    frob:waive LARGE001

    reasoning added, both comment-only changes -- no runtime behavior

    changed by either). One genuine split seam identified (telemetry.py)

    and filed separately rather than attempted under this pass''s time

    budget. Remaining ~80 files carried forward to a fresh successor ticket

    (T-2695) rather than left as an indefinitely-open umbrella --

    same closure discipline this repo''s own T-1651/T-1656/T-1661/T-1608-

    style umbrella tickets already use (finite batch, explicit successor for

    the rest). No behavioral delta: both waivers are comments (frob:waive

    directives), gate:LARGE stayed WARN-tier throughout (0 errors before and

    after), and no other file was touched.'
  actor: logan
  at: '2026-08-19'
  old_length: 3312
  new_length: 4084
evidence:
- tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
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
time: a new module needs a design/frob.strata code= glob addition plus a
hand-declared `interface=` update (T-1870: <!-- frob:waive DOC006 reason="naming the T-1870-removed command for historical context, not claiming it currently exists" -->`frob sys sync-interface`'s
auto-writer was removed; `interface=` is now purely hand-declared, no
CLI command re-runs it); prose separated from its frob:invariant anchor
needs the anchor (or its waiver) carried forward explicitly as
carried-forward, not a new claim.

frob:no-behavior-change reason="Batch-1 outcome: 2 files disposed (real per-file frob:waive LARGE001
reasoning added, both comment-only changes -- no runtime behavior
changed by either). One genuine split seam identified (telemetry.py)
and filed separately rather than attempted under this pass's time
budget. Remaining ~80 files carried forward to a fresh successor ticket
(T-2695) rather than left as an indefinitely-open umbrella --
same closure discipline this repo's own T-1651/T-1656/T-1661/T-1608-
style umbrella tickets already use (finite batch, explicit successor for
the rest). No behavioral delta: both waivers are comments (frob:waive
directives), gate:LARGE stayed WARN-tier throughout (0 errors before and
after), and no other file was touched."