---
id: T-2370
title: Burn COV006/COV007 WARN gates to zero, then promote to error
state: in-progress
kind: bug
origin: agent
created: '2026-08-17'
priority: medium
parent: T-0969
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: rollup epic burning COV006/COV007 to zero then promoting
  WARN->error; batched per T-2359/T-2373 precedent into child tickets, each with its
  own real scope
body_changes:
- mode: append
  reason: record the measured REAL GAP / HONEST WAIVE / DETECTOR BUG split so the
    next agent does not re-derive it, and so the promotion half is not attempted while
    132 findings remain
  actor: logan
  at: '2026-08-18'
  old_length: 1314
  new_length: 4507
designated_repro_test: null
acceptance:
- text: given the family's WARN codes, when frob check --json runs, then zero findings
    remain
  evidence: []
- text: given the family's gate module, when its severity is read, then it is ERROR
    not WARNING
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured via `uv run frob check --json --budget 500` (full gate-summary coverage,
no BUDGET001 deferral) piped through `scripts/check_summary.py`, 2026-08-18.

WARN-tier finding count, this family (doc/test coverage secondary checks): 64 across codes COV006, COV007.

Do NOT hand-count with grep -- this repo has measured false zeros that way, including
one tonight. Re-measure with the same command above before starting and before
claiming done; treat any disagreement with the number in this body as the tree
having moved, not as your measurement being wrong.

Closure is two-part per the epic (T-0969):
1. Zero findings for every code above, verified via the same
   `frob check --json --budget 500 | python3 scripts/check_summary.py` command.
2. Each code above promoted from warning to error severity in its gate module
   (grep the gate module for its severity constant/mapping) -- a burn-down that
   stops at zero and leaves the gate advisory lets the debt silently reaccumulate.
   DOC012 and the T-1662 arc both closed correctly today by doing both; follow
   that shape, not a zero-only burn-down.

Narrow `scope` to the actual files this family's findings live in once you've
run the gate and can see them -- do not take a broad blanket scope; this keeps
you disjoint from sibling children of T-0969.


TRIAGE RESULT (2026-08-18, every live finding sorted into exactly one
category; measured unbudgeted via `frob check --only coverage --json`,
counting severity="warning" only -- "note" is the already-waived tier and
counting it inflates the bucket from 157 to 344).

Starting count 157 (COV007 139, COV006 18). The coordinator's older
figures (COV007 105, COV006 18) were stale by 34 on COV007.

  REAL GAP .......  0
  HONEST WAIVE ... 36
  DETECTOR BUG ... 121  (3 classes)

DETECTOR BUG, class 1 -- COV007 vs strata clearance: 25. FIXED AND
LANDED as T-2549 (ef519d6a0). `RawSymbol.public` for a `.strata` symbol
is the node's declared SECURITY CLEARANCE (`_walk_strata._build_symbol`,
T-2410), not API privacy, so every `trusted`/`internal` component read as
a private helper. `_cov007` now skips non-python src files, mirroring
`_cov006_edge_violation`'s existing non-python skip. Count after: 132.

DETECTOR BUG, class 2 -- COV006 call-graph blindness: 18. Filed as
T-2550. All 18 test bodies were read individually. `build_call_graph`
never records an edge into a PUBLIC callee, and the compensating rescue
only covers a public wrapper in the TARGET'S OWN FILE called by name from
the test body. Every finding is outside that shape: (a) the test reaches
the private target through a public entry in a different file/package
re-export several hops out (test_vet.py, test_ticket_land.py), or (b) the
test calls that entry from a TEST-CLASS HELPER METHOD rather than the
test body (all six test_lang.py findings). Zero are unexercised bindings.

DETECTOR BUG, class 3 -- COV007 mis-scoped for files with no public
surface: 78. Filed as T-2551. scripts/fleet_status.py (40) and three
.claude/hooks/*.py (38) are standalone executables whose entire surface
is `main()` plus private helpers by design; the rule's remedy ("move it
onto the public caller") is unperformable there, and performing it would
collapse per-symbol doc obligations onto one symbol and destroy the
digest bindings AFFECT001/DRIFT001 depend on.

HONEST WAIVE: 36 -- private helpers in src/frob/** carrying a DELIBERATE
per-symbol doc anchor that names them (e.g. `_refuse_over_broad_scope_on_
start` -> tickets-data-storage.md#mega-glob-scope-refused-at-start-t-1866,
`_attribute_new_findings` -> tickets-verify-sweep.md#symbolic-attribution
-t-1690, `_widen_node_grants` -> strata/surface.md#fragments-t-2502). The
rule's own docstring names this as legitimate and asks for human
confirmation, i.e. a waiver. NOT yet written: 36 individually-reasoned
waivers are worth writing only after T-2551 decides whether the rule is
being narrowed anyway, and the repo already carries ~100 near-identical
COV007 waiver texts (T-1636/T-0871), which is itself evidence the rule
wants redesign rather than more boilerplate.

PROMOTION IS BLOCKED, and specifically must not be done for COV006 even
at zero: its own docstring states WARN is deliberate because
`frob.graph.callgraph` is an explicitly best-effort name-based resolver.
Promoting a heuristic built on an unsound graph to a land-blocking ERROR
is the same mistake class this repo already paid for once.

REMAINING TO ZERO: 132 = 18 (T-2550) + 78 (T-2551) + 36 (waivers).
