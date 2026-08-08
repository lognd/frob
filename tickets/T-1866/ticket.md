---
id: T-1866
title: 'frob ticket start must REFUSE a mega-glob scope, not merely warn: 39 of 72
  queued tickets lock a whole tree'
state: queued
kind: feature
origin: human
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/tickets/_scope_breadth.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Scope IS the lease. A ticket whose scope contains `tests/**` or
`docs/**` locks every other agent out of that entire tree the moment it
is started. This is the dominant throughput limiter on this repo, and
it is not a per-ticket authoring mistake -- it is systemic.

MEASURED, 2026-08-08: **39 of 72 queued tickets** declare at least one
mega-glob. The census by glob:

    tests/**                        24 tickets
    docs/**                         20 tickets
    src/frob/**                      7 tickets
    src/frob/gates/**                5 tickets
    src/frob/tickets/**              4 tickets
    src/frob/strata/**               3 tickets
    src/frob/app/ticket_runner/**    2 tickets
    src/frob/vet/**                  1 ticket

Over half the queue cannot be dispatched next to another agent without
the coordinator hand-narrowing it first. That hand-narrowing happened
four times today (T-1623, T-1628, T-1629, T-1662) and is pure
coordinator toil that will recur on every future ticket.

THE MECHANISM ALREADY EXISTS AND IS TOO WEAK.

- `TICK009` (`_tick009_scope_breadth_nudges`) emits a WARN per nudge,
  but DELIBERATELY skips `QUEUED` tickets. T-1645's reasoning for that
  exemption is sound and should NOT be reverted: a queued ticket's scope
  is a PREDICTION made before anyone opened the code, and demanding
  file-level precision then produces either an invented-wrong narrow
  list or a permanent warning nobody can act on.
- `_warn_scope_breadth_on_start` surfaces the same nudge at
  `frob ticket start` -- which is exactly the right moment, because the
  author now has the code open and a broad scope has started costing
  other tickets. But it only WARNS. The agent reads the warning, shrugs,
  and takes the whole-tree lease anyway. Observed repeatedly today.
- `scope_breadth_ack` (`frob ticket scope-ack`, T-1484) already exists
  as the deliberate escape hatch for a genuinely broad epic.

So every part needed is already built. The only thing missing is teeth.

REQUIRED: make `frob ticket start` REFUSE a scope containing a mega-glob
instead of warning about it. Name the offending globs and the remedy in
the refusal. `frob ticket scope-ack` remains the documented escape for a
ticket whose honest scope really is a package glob.

This ADDS NO NEW MECHANISM -- it promotes an existing warning to a
refusal and reuses the existing ack channel as the escape. That is the
cheap direction. Do NOT build a new "scope advisor", a narrowing
suggester, or a second waiver family; this repo's standing lesson is
that a rule which lives only in prose (or only in a WARN) protects
nothing. INV006 sat at 338 waivers and 0 findings before deletion;
T-1733's silent evidence unbinding and the `--force` family that logged
nothing are the same shape. A warning that is always ignored is not a
guard, it is noise with a good conscience.

DEFINE "mega-glob" precisely and by measurement, not by taste. The
natural rule is a glob whose match set exceeds some fraction of the
repo, or that spans a whole top-level tree. `large_glob_warnings`
(T-0453) already computes the match sets via `scope_breadth_context` --
reuse that computation rather than pattern-matching the literal string
`**`, so the threshold stays semantic and not lexical. A scope of
`src/frob/gates/_coverage.py` and a scope of `docs/**` differ by what
they MATCH, not by how they are spelled.

KEEP THE QUEUED EXEMPTION. Refusal belongs at `start`, where the
information exists to narrow correctly and where the damage actually
begins.
