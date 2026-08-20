---
id: T-2740
title: 'waive-audit cannot distinguish a necessary waiver from an inert one: 11 RENDER001
  waivers sat on paths the gate never scanned'
state: in-progress
kind: bug
origin: human
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_render_lint.py
- src/frob/app/ticket_runner/_waive_audit.py
- src/frob/_cli_parsers/_ticket/*.py
- tests/unit/test_waive_audit_runner.py
- tests/test_gates.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_render_lint.py
  reason: 'T-2740: report per-waiver liveness (necessary/inert/obsolete) alongside
    honest/cop-out; touches the waive-audit runner, its CLI wiring, a RENDER001 scan-membership
    helper, and their tests'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_waive_audit.py
  reason: 'T-2740: report per-waiver liveness (necessary/inert/obsolete) alongside
    honest/cop-out; touches the waive-audit runner, its CLI wiring, a RENDER001 scan-membership
    helper, and their tests'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/_cli_parsers/_ticket/*.py
  reason: 'T-2740: report per-waiver liveness (necessary/inert/obsolete) alongside
    honest/cop-out; touches the waive-audit runner, its CLI wiring, a RENDER001 scan-membership
    helper, and their tests'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/unit/test_waive_audit_runner.py
  reason: 'T-2740: report per-waiver liveness (necessary/inert/obsolete) alongside
    honest/cop-out; touches the waive-audit runner, its CLI wiring, a RENDER001 scan-membership
    helper, and their tests'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_gates.py
  reason: 'T-2740: report per-waiver liveness (necessary/inert/obsolete) alongside
    honest/cop-out; touches the waive-audit runner, its CLI wiring, a RENDER001 scan-membership
    helper, and their tests'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/config.py
  reason: 'T-2740: --check-liveness flag wiring needs an AppConfig field (config.py)
    and BOOL_FLAGS coverage entry (_config_external.py), same pattern as T-2496''s
    --check-collisions'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'T-2740: --check-liveness flag wiring needs an AppConfig field (config.py)
    and BOOL_FLAGS coverage entry (_config_external.py), same pattern as T-2496''s
    --check-collisions'
  actor: logan
  at: '2026-08-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## The finding that motivates this

T-2719 discovered that RENDER001's scan pathspec was hardcoded to
`src/frob`, so `.claude/hooks/*.py` and `scripts/fleet_status.py` were
NEVER SCANNED. The 11 `frob:waive RENDER001` directives sitting in those
files were therefore INERT -- suppressing nothing, because nothing ever
fired there.

Widening the scan revealed 28 genuine RENDER001 violations in those same
files, previously invisible.

## Why this undermines a conclusion already drawn

T-1614's waiver audit (landed 9681080a9) classified 100 `frob:waive`
directives and reported **0 cop-outs, 100 still necessary and honest**.
I accepted that result. But the audit judges a waiver's REASON -- whether
the stated justification is specific and truthful. It does not, and
cannot as built, establish that the waiver is doing anything.

A waiver can be:
  (a) necessary  -- the finding fires and the waiver suppresses it
  (b) inert      -- the gate never scans that path, so nothing fires
  (c) obsolete   -- the finding no longer reproduces

The audit distinguishes honest from cop-out. It does not distinguish (a)
from (b). At least 11 of the directives in this repo were (b), and we only
learned that because a separate ticket happened to widen a scan.

## Why (b) is worse than (c)

An obsolete waiver is harmless clutter. An INERT waiver is actively
misleading in two directions at once: it asserts that a rule applies to a
file the gate never examines, and it conceals that the file is unscanned.
Anyone reading it -- including the audit -- reasonably infers coverage that
does not exist. The 28 real violations sat behind that inference.

## What to build

Extend `frob ticket waive-audit scan` to report LIVENESS alongside
honesty: for each directive, does its rule actually scan that path, and
does the finding reproduce there? Classify into necessary / inert /
obsolete rather than only honest / cop-out.

CRITICAL CONSTRAINT: do NOT let this become a bulk-removal mechanism. A
prior rule-level liveness cleanup in this repo shipped once and DELETED 55
LIVE WAIVERS -- rule-level liveness reasoning is unsound and the guards are
hardened deliberately. This must REPORT the classification. Removal stays
a per-site human/agent judgement with a stated measurement.

An INERT verdict should also be treated as a finding about the GATE, not
just the waiver: an unscanned path that people are writing waivers for is
evidence the gate's pathspec is wrong. That is how T-2719 was found.

## Positive controls, both directions

- a waiver on a path its rule does not scan is reported INERT
- a waiver actively suppressing a reproducing finding is reported
  NECESSARY -- never inert
- a waiver whose finding no longer reproduces on a scanned path is
  reported OBSOLETE, distinctly from inert
- the audit's existing honest/cop-out judgement is unchanged for all three

## Related

This is the third hardcoded-path defect measured today, all the same
PORT001 class: LANG004 emitting frob's own `src/frob/` paths into consumer
repos (T-2706), `fleet_status.py` resolving its repo root via `__file__`
and reporting 0 leases from a worktree (T-2677), and now RENDER001's
scan pathspec. Declare, never hardcode.
