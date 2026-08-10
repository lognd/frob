---
id: T-1981
title: 'Burn down SYS110_UNAUDITED_NODES: T-1629''s rule enforces on 2 of 17 nodes
  until the 15 exempted mirrors are hand-audited'
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/_selfconform.py
- design/frob.strata
- tests/unit/strata/test_selfconform.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: per-node interface= audit fixes live in design/frob.strata, the design model
    file itself -- the ticket's declared scope (_selfconform.py) is where the exemption
    frozenset lives, not where the hand-declared interface= blocks being audited live
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: acceptance test for the burn-down (asserting the exemption set shrinks and
    never widens) lives in this existing test module
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_burn_down_shrinks_the_exemption_never_widens_it
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1629 shipped SYS110 (a node's real public surface must be a subset of
its hand-declared `interface=`), but exempted 15 of the 17 nodes that
have `interface=` blocks via `SYS110_UNAUDITED_NODES`
(`frob.strata._selfconform`). The rule therefore enforces on 2 nodes.

The exemption was correct and correctly disclosed: those 15 carry stale
T-0668-era GENERATED mirrors, measured at 734 findings of real drift, and
enabling the check unconditionally would have broken `TestRealGateGreen`.
Phasing was the right call. This ticket is the other half -- without it
the exemption is permanent and SYS110 is decorative for 88% of its
domain.

WHY THIS NEEDS ITS OWN TICKET: a hand-typed exemption frozenset inside a
source file is not tracked by any queue. T-1629 is `done` and archives;
nothing then reports that 15 nodes are unaudited, and no gate fails
while they remain. That is the catalogued-is-not-enforced shape --
compare T-1960, where 7 "wire X into Y" follow-ups sat at medium and
starved because nothing carried the pressure forward.

It is also the shape recorded from T-1967 earlier today: an exemption
that covers the normal case turns a guard off while leaving it looking
green. Here the exemption covers 15/17 of the population.

MEASURED:
- `SYS110_UNAUDITED_NODES` in `src/frob/strata/_selfconform.py`: 15 node
  ids exempted.
- Enforced today: `checker`, `fleet` only.
- Drift behind the exemption: 734 findings across the 15, per T-1629's
  own measurement.

THE WORK: audit each exempted node's `interface=` block, replace the
stale generated mirror with hand-declared INTENDED surface, and remove
that node id from the frozenset. One node per commit is fine and
probably safer; the goal is the frozenset reaching empty and being
deleted along with the code that reads it.

DO NOT FIX IT THIS WAY:
- Do NOT auto-generate the corrected `interface=` blocks. T-1870 DELETED
  the auto-measured mirror on an explicit owner directive that no code
  path may auto-update declared public-symbol surface, and T-1629's
  whole premise is that `interface=` means hand-declared INTENT.
  Regenerating the mirror would restore precisely what both tickets
  removed, while making SYS110 pass. That is the tempting shortcut and
  it inverts the point of the rule.
- Do NOT empty the frozenset without auditing, to "turn the rule on".
  That converts 734 disclosed findings into 734 gate errors on main and
  reds the floor for everyone.
- Do NOT widen the exemption to silence a node that turns out to be
  hard.

ACCEPTANCE: first test must FAIL before the fix -- assert
`SYS110_UNAUDITED_NODES` is smaller than its current 15 (and ultimately
empty). Per node removed, record the before/after finding count for that
node and confirm the unscoped floor stays at its current value. When the
frozenset reaches empty, delete it and the branch that consults it.

## Done report

T-1629's SYS110 exemption frozenset covered 15/17 nodes with real drift (734 findings, measured at T-1629 time). Audited the smallest exempted node first (natives, a 3-entry interface= block): _load_audit_model + check_self_conformance with the exemption temporarily lifted (measurement only, not committed) found exactly 1 real finding -- CARGO_CACHE_DIRNAME, which is genuinely in the module's own __all__ and consumed by tests/unit/test_natives_build.py, so it belongs in interface= by hand-audited intent, not by regenerating a mirror. Added it by hand, removed natives from SYS110_UNAUDITED_NODES, re-measured: 0 findings for natives, 0 findings introduced anywhere else. 14 nodes remain exempted; each needs its own per-node audit in a follow-up pass -- this ticket demonstrates the process and clears the first (smallest) node rather than rushing all 15.

### Changed
```
 tickets/T-1981/ticket.md | 20 +++++++++++++++++++-
 1 file changed, 19 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_burn_down_shrinks_the_exemption_never_widens_it` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, DSL001@docs/commands/sys.md, DSL001@docs/design/coding-performance-corpus.md, DSL001@docs/design/cwe-1000-registry.md, DSL001@docs/design/design-pattern-traps-corpus.md, DSL001@docs/design/language-adapter-tier-decision.md, DSL001@docs/design/registry/RECONCILIATION.md, DSL001@docs/design/system-performance-corpus.md, DSL001@docs/guides/coordinator-scripts.md, DSL001@docs/guides/editors.md, DSL001@docs/guides/exhaustive-research.md, DSL001@docs/guides/install.md, DSL001@docs/modules/app.md, DSL001@docs/modules/arch.md, DSL001@docs/modules/bind.md, DSL001@docs/modules/clean.md, DSL001@docs/modules/cli.md, DSL001@docs/modules/cve.md, DSL001@docs/modules/decisions.md, DSL001@docs/modules/deploy.md, DSL001@docs/modules/dup-sota-survey.md, DSL001@docs/modules/dup.md, DSL001@docs/modules/fleet.md, DSL001@docs/modules/fuzz.md, DSL001@docs/modules/gates.md, DSL001@docs/modules/graph.md, DSL001@docs/modules/lang.md, DSL001@docs/modules/logging.md, DSL001@docs/modules/mutate.md, DSL001@docs/modules/perf.md, DSL001@docs/modules/process.md, DSL001@docs/modules/release.md, DSL001@docs/modules/render.md, DSL001@docs/modules/serve.md, DSL001@docs/modules/stats.md, DSL001@docs/modules/strata.md, DSL001@docs/modules/testing.md, DSL001@docs/modules/tickets.md, DSL001@docs/modules/vet.md, DSL001@docs/strata/boundary.md, DSL001@docs/strata/charter.md, DSL001@docs/strata/evidence.md, DSL001@docs/strata/host.md, DSL001@docs/strata/kernel.md, DSL001@docs/strata/krb.md, DSL001@docs/strata/policy.md, DSL001@docs/strata/reliability.md, DSL001@docs/strata/roadmap.md, DSL001@docs/strata/selfconform.md, DSL001@docs/strata/surface.md, DSL001@docs/strata/threat.md, DSL001@docs/strata/waive.md, F401@/home/logan/projects/frob/.claude/worktrees/queue-hygiene/tests/unit/test_tickets_evidence_only_scope.py
