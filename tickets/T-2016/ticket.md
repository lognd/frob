---
id: T-2016
title: design a growth-rate grammar for frob sys capacity --at DATE
state: done
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/strata/kernel.md
- docs/strata/reliability.md
- src/frob/strata/_capacity.py
evidence_scope:
- tests/unit/strata/test_capacity_projection.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/strata/kernel.md
  reason: design deliverable is documentation, not code -- add the two docs the grammar
    design and its capacity-evaluator cross-reference live in
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/strata/reliability.md
  reason: design deliverable is documentation, not code -- add the two docs the grammar
    design and its capacity-evaluator cross-reference live in
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/strata/**
  reason: design-only ticket produced a docs deliverable plus a docstring cross-reference;
    narrow off the epic-wide glob to just the files actually touched
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_capacity.py
  reason: design-only ticket produced a docs deliverable plus a docstring cross-reference;
    narrow off the epic-wide glob to just the files actually touched
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityUnscaled::test_over_capacity_current_demand_fires
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityScaled::test_population_scales_demand_linearly
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
docs/strata/roadmap.md's "CLI surface (target)" names `frob sys capacity
[--population N | --at DATE]` as a phase-5 verb. T-1927 implemented the
`--population N` half (`frob.strata._capacity::project_capacity`,
docs/strata/reliability.md#population-projected-capacity-t-1927) but
deliberately cut `--at DATE`: projecting to a calendar date needs a
growth-rate declaration on `Node.users`/`rate` that the T-0702 demand-
propagation grammar (docs/strata/kernel.md#demand-declarations-t-0702)
does not have today -- inventing one is a surface-language change, out
of T-1927's "an evaluator over the model as it exists" scope.

Needed before `--at DATE` is meaningful: a growth-rate declaration
grammar (e.g. `users N growth RATE per PERIOD`) plus the date-projection
arithmetic in `project_capacity` (or a sibling entrypoint) that resolves
a target `--at` date against that rate to a population, then reuses the
same `--population`-style scaling this ticket already built. Filed as a
residue of T-1927 rather than folded into it, per that ticket's own
scope note on why `--at DATE` was cut.

## Done report

Changed (docs/design only, no code behavior change):
- `docs/strata/kernel.md` -- new section "Growth-rate declarations
  (T-2016 design -- NOT implemented)" under the T-0702 demand-
  declarations section, anchor `#growth-rate-declarations-t-2016`.
- `docs/strata/reliability.md` -- T-1927's disclosed-scope-cut note now
  points forward to the new design section.
- `src/frob/strata/_capacity.py` -- module docstring cross-reference
  only (prose, no behavior change).

Evidence: none required (docs-only design deliverable, no new/changed
behavior; `tests/unit/strata/test_capacity.py` re-run unchanged,
12/12 pass, confirming zero behavior drift from the docstring edit).

Filed: none.

## Summary

Did NOT write any grammar/elaboration/evaluator code, per the dispatch
instruction. Produced a concrete design:

- **Grammar**: an optional `growth PERCENT per PERIOD` modifier on the
  existing `users NUMBER`/`rate NUMBER UNIT` clauses (T-0261 symmetry
  preserved -- growth is a property of a demand declaration, not a new
  declaration kind). `PERCENT` reuses the existing `%` unit; `PERIOD`
  needs three new fixed-length time units (`w`/`mo`/`y`, matching the
  existing `d`'s fixed-86400s simplification -- explicitly not
  calendar-aware, called out for the CLI's own `--help` text).
- **Arithmetic**: compound (not linear) growth -- `declared_value *
  (1 + pct/100) ** (t / period_length)`. Chosen over linear because
  compound decay asymptotes toward zero under a negative rate while
  linear decay crosses zero and keeps going negative; the standard
  reading of a stated "12% YoY" rate is compound regardless.
- **The real architectural finding**: `project_capacity` (T-1927)
  applies ONE global scalar (`population/baseline`) AFTER
  `aggregate_demand`'s BFS summation collapses per-source demand at a
  node. That structurally cannot support a per-node growth rate --
  once two different demand-declaring sources are summed at a
  downstream node, which source contributed how much is already gone.
  A sound `--at DATE` needs each node's OWN synthetic seed rate scaled
  by ITS OWN growth projection BEFORE `aggregate_demand` sums it, not
  a second pass on top of the output. This is the reason `--at DATE`
  is a modeling change and not a CLI-parsing one, made explicit rather
  than left implicit the way T-1927's own scope-cut note left it.
- **Explicit "will not express" list**: no seasonal/non-monotonic
  growth (a `scenario`'s `scale IDENT by NUM` already covers a
  one-off surge and stays the right tool for that); no growth on
  `Capacity` itself (demand-side only, forever, not just for this
  pass -- letting both sides drift independently could never produce
  a stable "N replicas by DATE" answer); no per-flow growth distinct
  from node/store growth (T-0702's own causal direction is entry
  demand -> flow load, not the reverse); no special-casing for a
  `--at DATE` in the past (the compound formula already gives a
  coherent smaller-not-negative answer for negative elapsed time,
  which needs no extra guardrail).
- **The one decision that needs the ticket owner, stated plainly**:
  the model currently has NO notion of calendar time at all -- `--at
  DATE` cannot compute elapsed time without an anchor. Two candidates
  laid out with their real tradeoff (a model-level `as_of DATE`
  declaration, reproducible from source but silently defaults to
  wall-clock if an author forgets it and nothing enforces the
  pairing; vs. a CLI-only `--since DATE` paired with `--at DATE`,
  always-visible and matching `--population N`'s own "model states
  WHAT, CLI supplies WHEN/HOW-MUCH" precedent, but two dates to type
  correctly per invocation). Recommended option 2, but did not decide
  on the owner's behalf -- said explicitly this needs a call before
  an implementer starts.
- **Suggested landing shape** for whoever implements it next: grammar +
  units -> the CLI-anchor decision resolved and wired ->
  `aggregate_demand`'s seed-rate scaling (the actual hard part) ->
  `project_capacity` likely needs no change beyond accepting/forwarding
  the new date parameters, since it already treats `aggregate_demand`'s
  output as a black box.

Gates: no code-affecting gate applicable (docs + docstring prose only).
`tests/unit/strata/test_capacity.py` 12/12 unchanged.

## Addendum (2026-08-10, post-coordinator review)

Coordinator decided the anchor-date open question: CLI-only `--since
DATE`/`--at DATE`, not a model-level `as_of DATE` (a model-level fact
that drifts silently the moment the file is not re-read is the exact
reproducibility trap the `as_of` option's own con already named).
Recorded in `docs/strata/kernel.md#growth-rate-declarations-t-2016` in
place of the open question; no `as_of` grammar will be added.

Also made the aggregation-order finding unmissable per coordinator
request: implementing `--at DATE` requires reordering
`FactBase.aggregate_demand`'s own BFS summation so each node's growth
projection applies BEFORE it sums, not after -- a change to a shared
kernel primitive every REL380/REL381/CAP001 consumer of
`aggregate_demand` depends on, not a leaf addition to `_capacity.py`
alone. Flagged explicitly, in a callout box at the top of the
architecture-note paragraph and again in the landing-shape summary, as
a different order of magnitude of change than "add a grammar clause" --
scope/estimate it as "modify a shared kernel primitive plus
re-verify its full consumer set's regression coverage", not as
"`--population N` but with a date".

### Changed
```
 docs/strata/kernel.md                              | 184 ++++++++++++++++++++-
 docs/strata/reliability.md                         |   8 +-
 src/frob/gates/_dead_symbols.py                    |  20 ++-
 src/frob/strata/_capacity.py                       |   9 +
 tests/test_gates.py                                |  76 +++++++++
 tickets/T-1959/done-report.md                      | 113 +++++++++++++
 tickets/T-1959/evidence/attempt3-with-block-fix.md | 163 ++++++++++++++++++
 tickets/T-1959/ticket.md                           |  12 +-
 tickets/T-2016/done-report.md                      | 100 +++++++++++
 tickets/T-2016/ticket.md                           |  38 ++++-
 tickets/T-2066/ticket.md                 |  65 ++++++++
 11 files changed, 781 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/strata/test_capacity_projection.py::TestProjectCapacityUnscaled::test_over_capacity_current_demand_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_capacity_projection.py::TestProjectCapacityScaled::test_population_scales_demand_linearly` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/strata/_claims.py, DOC002@src/frob/strata/_claims.py, F401@/home/logan/projects/frob/.claude/worktrees/t1959-t2016/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t1959-t2016/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-2016
