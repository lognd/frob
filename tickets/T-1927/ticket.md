---
id: T-1927
title: design a population/date-projected capacity evaluator for frob sys capacity
state: queued
kind: feature
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/T-1927/**
  reason: explicit self-scope so SCOPE001's cross-ticket exemption (frob.gates._commit_exempts_file)
    recognizes this ticket's own shard commit and does not flag it against the filing
    ticket T-1480
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: tickets/T-1927/**
  reason: this self-scope grant never actually fixed SCOPE001 (frob.gates.__init__._TICKET_REF_RE
    only matches T-#### 4-digit ids in commit subjects, never a T-draft-<hex> id,
    so the cross-ticket exemption could never engage regardless) and land-parity already
    reports 0 unscoped errors without it; removing to reduce surface for the T-1918
    sibling-draft-finalize lease-collision land bug
  actor: logan
  at: '2026-08-09'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
docs/strata/roadmap.md's "CLI surface (target)" names `frob sys capacity
[--population N | --at DATE]` as a phase-5 verb. T-1480 investigated and
found: no existing evaluator projects capacity thresholds against a
POPULATION or DATE parameter at all (`_starvation.py`'s capacity checks
are static, not projected) -- this is new modeling work, not a CLI-glue
gap over an existing evaluator (unlike `trace`, which T-1480 built as a
thin wrapper over the already-shipped `FactBase.reachable`).

Needed before a CLI verb here is meaningful: a real
population/date-projected capacity evaluator in `frob.strata`, analogous
to how `FactBase.reachable`/`propagated_demand` already model influence
closure and load propagation. Filed as a residue of T-1480 rather than
folded into it, per that ticket's own scope note on why `capacity` was
cut.
